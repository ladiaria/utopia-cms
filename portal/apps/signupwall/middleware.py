# -*- coding: utf-8 -*-

from inflect import engine

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.urls import resolve, reverse
from django.urls.exceptions import Resolver404
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.utils.deprecation import MiddlewareMixin

from apps import mongo_db
from signupwall.utils import get_ip
from core.models import Article
from thedaily.email_logic import limited_free_article_mail


debug = getattr(settings, 'SIGNUPWALL_DEBUG', settings.DEBUG)


def number_to_words(number):
    return slugify(engine().number_to_words(number))


def get_article_by_url_kwargs(kwargs):
    try:
        return Article.objects.get(
            slug=kwargs['slug'], date_published__year=kwargs['year'], date_published__month=kwargs['month']
        )
    except Article.MultipleObjectsReturned:
        # TODO: Send a notification to "editors"
        raise Http404("Múltiples artículos con igual identificación en el mes.")


def get_article_by_url_path(url_path):
    try:
        return Article.objects.get(url_path=url_path)
    except Article.MultipleObjectsReturned:
        # TODO: Send a notification to "editors"
        raise Http404("Múltiples artículos con igual identificación en el mes.")


def get_session_key(request):
    if settings.SESSION_COOKIE_NAME in request.COOKIES:
        # use the sessionid cookie as key
        session_key = request.COOKIES[settings.SESSION_COOKIE_NAME]
    else:
        # if not present, generate it
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

    if mongo_db is not None:
        result = mongo_db.signupwall_visitor.insert_one(
            {'session_key': session_key, 'ip_address': ip_address, 'timestamp': timezone.now()}
        )
        # generation time can be obtained in the returned value .get('_id').generation_time (TODO: re-check this)
        return mongo_db.signupwall_visitor.find_one({'_id': result.inserted_id})


def subscriber_access(subscriber, article):
    """
    Returns True if the subscriber has subscriber access to the article, otherwise returns False
    The logic applied is to give access if the subscriber is subscribed to the default pub or when the article is not
    full restricted, to any pub that the article is published in (if it's not a restricted article, otherwise the
    subscriber must be subscribed to the main pub of the article), or to any pub in article's additional_access field.
    """
    restricted_article = article.is_restricted()
    return (
        subscriber.is_subscriber()

        or

        not article.full_restricted and (

            not restricted_article
            and any(subscriber.is_subscriber(p.slug) for p in article.publications())

            or restricted_article
            and subscriber.is_subscriber(article.main_section.edition.publication.slug)

            or any(subscriber.is_subscriber(p.slug) for p in article.additional_access.all())

        )
    )


def is_google_amp(request):
    # TODO: implement the validation of Google requests made to feed its AMP cache
    return False


class SignupwallMiddleware(MiddlewareMixin):

    def anon_articles_visited_count(self, nowval, visitor, credits, debug=False):
        """
        anon users, count paths visited by session, we save at least 7-day back log.
        No need to count more paths than credits + 1 in the last 7 days.
        TODO: "credits" seems to be kindof reserved word (try to use a better var name for it)
        """
        paths_visited, articles_visited_count, dt = set(), 0, nowval - timedelta(7)
        for v in mongo_db.signupwall_visitor.find(
            {'session_key': visitor.get('session_key'), 'timestamp': {'$gt': dt}}
        ):
            paths_visited.add(v.get('path_visited'))
            articles_visited_count = len(paths_visited)
            if articles_visited_count > credits:
                break

        if debug:
            print(
                'DEBUG: signupwall.middleware.process_request - articles_visited_count (session): %d' % (
                    articles_visited_count
                )
            )

        if articles_visited_count <= credits:
            # also search visits made with the session ips using other sessions
            for v in mongo_db.signupwall_visitor.find(
                {
                    'session_key': {'$ne': visitor.get('session_key')},
                    'timestamp': {'$gt': dt},
                }
            ):
                paths_visited.add(v.get('path_visited'))
                articles_visited_count = len(paths_visited)
                if articles_visited_count > credits:
                    break

        if debug:
            print(
                'DEBUG: signupwall.middleware.process_request - articles_visited_count (session+ips): %d' % (
                    articles_visited_count
                )
            )

        return articles_visited_count

    def process_request(self, request):

        # try to resolve path and get the target article
        try:
            path_resolved = resolve(request.path)
        except Resolver404:
            return

        if path_resolved.url_name == 'article_detail':
            try:
                article = get_article_by_url_path(request.path)
                # ignore AMP-feeding requests by Google and also AMP requests in "simulation"
                if (
                    is_google_amp(request)
                    or (
                        getattr(settings, 'AMP_SIMULATE', False)
                        and request.GET.get(settings.AMP_TOOLS_GET_PARAMETER) == 'amp'
                    )
                ):
                    return
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

        user_is_authenticated = user.is_authenticated

        # ignore also signupwall if the user has subscriber_access to the article
        if (
            article.is_public()
            or user_is_authenticated
            and hasattr(user, 'subscriber')
            and subscriber_access(user.subscriber, article)
        ):
            if debug:
                print('DEBUG: signupwall.middleware.process_request - subscribed user or public article')
            request.article_allowed = True
            return
        elif debug:
            print('DEBUG: signupwall.middleware.process_request - non subscribed user')
            print('DEBUG: signupwall.middleware.process_request - requested URL: %s' % request.get_full_path())

        # useful flag for a restricted_article, no credits should be spent because the user will not be allowed to read
        # this article.
        request.restricted_article = restricted_article = article.is_restricted_consider_full()

        visitor = None
        # if not restricted article and log views is enabled, set the path_visited to this visitor.
        if not restricted_article and settings.CORE_LOG_ARTICLE_VIEWS and mongo_db is not None:
            visitor = get_or_create_visitor(request)
            mongo_db.signupwall_visitor.update_one(
                {'_id': visitor.get('_id')}, {'$set': {'path_visited': request.path}}
            )

        if user_is_authenticated:

            # At this point the user is not anon and not subscribed, so we count all non-allowed articles visited
            # for the user in this month and add 1 if this article is not restricted and is not in the set,
            # we not need to know if there are more than credits+2.
            # Raise signupwall if the user has more than credits.
            credits = settings.SIGNUPWALL_MAX_CREDITS
            articles_visited = set() if restricted_article else set([article.id])
            articles_visited_count = len(articles_visited)
            if mongo_db is not None:
                for x in mongo_db.core_articleviewedby.find({'user': user.id, 'allowed': None}):
                    articles_visited.add(x['article'])
                    articles_visited_count = len(articles_visited)
                    if articles_visited_count >= credits + 2:
                        break

            if debug:
                print(
                    'DEBUG: signupwall.middleware.process_request - articles_visited_count (logged-in): %s'
                    % (articles_visited_count)
                )

        else:

            # anon users
            credits = settings.SIGNUPWALL_ANON_MAX_CREDITS
            if credits and visitor and mongo_db is not None:
                nowval = now()
                articles_visited_count = self.anon_articles_visited_count(nowval, visitor, credits, debug)
            else:
                articles_visited_count = 1

        if user_is_authenticated:
            if articles_visited_count == credits + 1:
                limited_free_article_mail(user)

        if (articles_visited_count > credits) or restricted_article:
            if settings.SIGNUPWALL_RISE_REDIRECT:
                if restricted_article:
                    request.signupwall = True
                else:
                    if user_is_authenticated:
                        urlname, reverse_kwargs = "subscribe", {"planslug": "DDIGM"}
                    else:
                        urlname, reverse_kwargs = "account-login", {}
                    # TODO: check redirect status code for the next line
                    return HttpResponseRedirect(reverse(urlname, kwargs=reverse_kwargs) + "?article=%d" % article.id)
            else:
                request.signupwall = True
        else:
            request.credits = credits - articles_visited_count
            request.signupwall_header = (
                settings.SIGNUPWALL_HEADER_ENABLED
                and user_is_authenticated
                and request.credits >= 0
                and not (settings.SIGNUPWALL_REMAINING_BANNER_ENABLED and user.subscriber.is_subscriber_any())
            )
            if request.signupwall_header:
                request.remaining_articles_word = number_to_words(request.credits)
