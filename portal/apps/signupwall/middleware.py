# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.http import Http404
from django.core.urlresolvers import resolve

from apps import core_articleviewedby_mdb, signupwall_visitor_mdb
from signupwall.utils import get_ip
from core.models import Article
from thedaily.email_logic import limited_free_article_mail


debug = getattr(settings, 'SIGNUPWALL_DEBUG', False)


def get_article_by_url_kwargs(kwargs):
    try:
        return Article.objects.get(
            slug=kwargs['slug'], date_published__year=kwargs['year'], date_published__month=kwargs['month']
        )
    except Article.MultipleObjectsReturned:
        # TODO: Send a notification to "editors"
        raise Http404(u"Múltiples artículos con igual identificación en el mes.")


def get_article_by_url_path(url_path):
    try:
        return Article.objects.get(url_path=url_path)
    except Article.MultipleObjectsReturned:
        # TODO: Send a notification to "editors"
        raise Http404(u"Múltiples artículos con igual identificación en el mes.")


def get_session_key(request):
    if settings.SESSION_COOKIE_NAME in request.COOKIES:
        # usa la cookie de sessionid como key
        session_key = request.COOKIES[settings.SESSION_COOKIE_NAME]
    else:
        # sino tiene le genera una
        request.session.save()
        session_key = request.session.session_key
    return session_key


def get_or_create_visitor(request):
    """
    # TODO: rename this function to "create_visitor" because it allways cretaes one, also update the docstring.
    Uses a MongoDB collection to store the visior and its paths visited, for performnce the collection should have
    indexes in some fields, create them according with portal/libs/scripts/one_time/20200814_migrate_visitorsmdb.py.
    returns: the visitor created or updated
    """
    session_key = get_session_key(request)
    if debug:
        print('DEBUG: signupwall.middleware.get_or_create_visitor - session_key: %s' % session_key)

    ip_address = get_ip(request)
    if debug:
        print('DEBUG: signupwall.middleware.get_or_create_visitor - ip_address: %s' % ip_address)

    if signupwall_visitor_mdb:
        result = signupwall_visitor_mdb.posts.insert_one(
            {'session_key': session_key, 'ip_address': ip_address, 'timestamp': datetime.now()}
        )
        # generation time can be obtained in the returned value .get('_id').generation_time (TODO: re-check this)
        return signupwall_visitor_mdb.posts.find_one({'_id': result.inserted_id})


class SignupwallMiddleware(object):

    def process_request(self, request):

        # resolve path and get the target article
        path_resolved = resolve(request.path)
        if path_resolved.url_name == 'article_detail':
            try:
                article = get_article_by_url_path(request.path)
            except Article.DoesNotExist:
                # ignore signupwall for not-found articles (core.views.article.article_detail will redirect if the
                # article is found in article's URL history)
                return
        else:
            # ignore signupwall for non article_detail paths
            if debug:
                print('DEBUG: signupwall.middleware.process_request - non article_detail path')
            return

        user = request.user

        # ignore also signupwall for staff members
        if user.is_staff:
            return

        user_is_authenticated = user.is_authenticated()

        # ignore also signupwall if the user is subscribed to the default pub
        # or to any pub that the article is published in
        if (user_is_authenticated and hasattr(user, 'subscriber') and (
                user.subscriber.is_subscriber() or any([
                    user.subscriber.is_subscriber(p.slug) for p in article.publications()]))):
            if debug:
                print('DEBUG: signupwall.middleware.process_request - subscribed user')
            return
        elif debug:
            print('DEBUG: signupwall.middleware.process_request - non subscribed user')
            print('DEBUG: signupwall.middleware.process_request - requested URL: %s' % request.get_full_path())

        visitor = None

        # dont spend a credit if the article is public
        if article.is_public():
            raise_signupwall = False
        else:
            raise_signupwall = True
            # if log views is enabled, set the path_visited to this visitor.
            if settings.CORE_LOG_ARTICLE_VIEWS and signupwall_visitor_mdb:
                visitor = get_or_create_visitor(request)
                signupwall_visitor_mdb.posts.update_one(
                    {'_id': visitor.get('_id')}, {'$set': {'path_visited': request.path}})

        if user_is_authenticated:

            # at this point, the user is not anon and not subscribed, so we can count all non-public articles visited
            # for the user in this month and add 1 if this article is not in the set and is not public, we not need to
            # know if there are more than credits+2.
            # raise signupwall if the user has more than credits
            credits = 10
            articles_visited = set() if article.is_public() else set([article.id])
            articles_visited_count = len(articles_visited)
            if core_articleviewedby_mdb:
                for x in core_articleviewedby_mdb.posts.find({'user': user.id, 'public': None}):
                    articles_visited.add(x['article'])
                    articles_visited_count = len(articles_visited)
                    if articles_visited_count >= credits + 2:
                        break

            if debug:
                print('DEBUG: signupwall.middleware.process_request - articles_visited_count (logged-in): %s' % (
                    articles_visited_count))
        else:

            # anon users, they will face the signupwall.
            articles_visited_count, credits = 1, 0

        if raise_signupwall and user_is_authenticated:
            if articles_visited_count == credits + 1:
                limited_free_article_mail(user)

        if raise_signupwall and (articles_visited_count > credits):
            # TODO: Why is this next function set here?
            request.signupwall = {'next': next}
        else:
            request.credits = credits - articles_visited_count
