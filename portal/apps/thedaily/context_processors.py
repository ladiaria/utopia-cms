
from builtins import str

import jwt
from time import time
from uuid import uuid4

from django.conf import settings
from django.urls import resolve, Resolver404
from django.contrib.flatpages.models import FlatPage

from core.models import Article, ArticleUrlHistory, Publication
from signupwall.middleware import get_article_by_url_kwargs, subscriber_access
from . import get_talk_url


def permissions(request):
    result, is_subscriber, is_subscriber_default, article = {}, False, False, None
    subscriber = getattr(request.user, 'subscriber', None)

    try:
        path_resolved = resolve(request.path)
        url_name = path_resolved.url_name
    except Resolver404:
        url_name = None

    if subscriber:
        is_subscriber_default = subscriber.is_subscriber()
        is_subscriber_any = subscriber.is_subscriber_any()
    else:
        is_subscriber_any = False

    # in the next lines, to determine if the user is a subscriber, we'll:
    # - use article.publications if this is an article detail page
    # - use publication if this is a publication home page
    if url_name == 'article_detail':
        try:
            article = get_article_by_url_kwargs(path_resolved.kwargs)
            is_subscriber = subscriber and subscriber_access(subscriber, article)
        except Article.DoesNotExist:
            # use url history and search again
            try:
                article = ArticleUrlHistory.objects.get(absolute_url=request.path).article
                is_subscriber = subscriber and subscriber_access(subscriber, article)
            except ArticleUrlHistory.DoesNotExist:
                # no article found, treat as if it was any other page
                is_subscriber = is_subscriber_default
    elif subscriber:
        if url_name == 'home':
            domain_slug = path_resolved.kwargs.get('domain_slug')
            if domain_slug and Publication.objects.filter(slug=domain_slug).exists():
                # not default pub home page
                is_subscriber = subscriber.is_subscriber(domain_slug)
            else:
                # default pub or area home page
                is_subscriber = is_subscriber_default
        else:
            is_subscriber = is_subscriber_default
            # other analog context variables for publications defined in settings
            result.update(
                ('is_subscriber_' + publication_slug, subscriber.is_subscriber(publication_slug))
                for publication_slug in getattr(settings, 'THEDAILY_IS_SUBSCRIBER_CONTEXT_PUBLICATIONS', ())
            )

    # A poll url path in google forms
    pu_path = getattr(settings, 'THEDAILY_POLL_URL_PATH', None) if request.user.is_authenticated else None
    result.update(
        {
            'is_subscriber': is_subscriber,
            'is_subscriber_default': is_subscriber_default,
            'is_subscriber_any': is_subscriber_any,
            'poll_url': ('https://forms.gle/' + pu_path) if pu_path else '',
        }
    )

    if article and article.allow_comments and get_talk_url():
        # if user is authenticated (or is_subscriber if configured by settings) generate the JWT for Coral Talk, also
        # for non-subscribers when article main section is one of the skipped sections by settings.
        talk_subscribers_only = getattr(settings, 'TALK_SUBSCRIBERS_ONLY', False)
        talk_subscribers_only_skip_sections = getattr(settings, 'TALK_SUBSCRIBERS_ONLY_SKIP_SECTIONS', ())
        auth_allowed = not talk_subscribers_only or (
            article.section and article.section.slug in talk_subscribers_only_skip_sections
        )
        result["talk_auth_allowed"] = auth_allowed
        if is_subscriber or (subscriber and auth_allowed):
            jti, exp = str(uuid4()), int(time()) + 60
            result['talk_auth_token'] = jwt.encode(
                {
                    'jti': jti,
                    'exp': exp + 3600,
                    'user': {
                        'id': str(request.user.id),
                        'email': request.user.email,
                        'username': request.user.get_full_name() or request.user.username,
                    },
                },
                settings.TALK_JWT_SECRET,
            )

    return result


def terms_and_conditions(request):
    result, fp_id = {}, settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID
    if fp_id:
        try:
            result['terms_and_conditions_url'] = FlatPage.objects.get(id=fp_id).get_absolute_url()
        except FlatPage.DoesNotExist:
            pass
    return result
