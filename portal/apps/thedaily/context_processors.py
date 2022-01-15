import jwt
from time import time
from uuid import uuid4

from django.conf import settings
from django.core.urlresolvers import resolve, Resolver404

from core.models import Article, ArticleUrlHistory, Publication
from signupwall.middleware import get_article_by_url_kwargs


def permissions(request):
    result, is_subscriber, is_subscriber_default = {}, False, False

    if request.user.is_authenticated() and hasattr(request.user, 'subscriber'):

        subscriber = request.user.subscriber

        # use article.publications if this is an article detail page
        # use publication if this is a publication home page
        try:
            path_resolved = resolve(request.path)
            url_name = path_resolved.url_name
        except Resolver404:
            url_name = None

        is_subscriber_default = subscriber.is_subscriber()
        is_subscriber_any = subscriber.is_subscriber_any()

        if url_name == 'article_detail':
            try:
                article = get_article_by_url_kwargs(path_resolved.kwargs)
                is_subscriber = is_subscriber_default or any(
                    [subscriber.is_subscriber(p.slug) for p in article.publications()])
            except Article.DoesNotExist:
                # use url history and search again
                try:
                    article = ArticleUrlHistory.objects.get(absolute_url=request.path).article
                    is_subscriber = is_subscriber_default or any(
                        [subscriber.is_subscriber(p.slug) for p in article.publications()]
                    )
                except ArticleUrlHistory.DoesNotExist:
                    # no article found, treat as if it was any other page
                    is_subscriber = is_subscriber_default
        elif url_name == 'home':
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
        result.update((
            'is_subscriber_' + publication_slug, subscriber.is_subscriber(publication_slug)
        ) for publication_slug in getattr(settings, 'THEDAILY_IS_SUBSCRIBER_CONTEXT_PUBLICATIONS', ()))

    else:
        is_subscriber_any = False

    # A poll url path in google forms
    pu_path = getattr(settings, 'THEDAILY_POLL_URL_PATH', None) if request.user.is_authenticated() else None

    result.update(
        {
            'is_subscriber': is_subscriber,
            'is_subscriber_default': is_subscriber_default,
            'is_subscriber_any': is_subscriber_any,
            'poll_url': (u'https://forms.gle/' + pu_path) if pu_path else u'',
        }
    )

    # if is_subscriber generate the JWT for Coral Talk integration (if TALK_URL is set)
    talk_url = getattr(settings, 'TALK_URL', None)
    if is_subscriber and talk_url:
        jti, exp = str(uuid4()), int(time()) + 60
        result['talk_auth_token'] = jwt.encode(
            {
                'jti': jti,
                'exp': exp + 3600,
                'user': {
                    'id': str(request.user.id), 'email': request.user.email,
                    'username': request.user.get_full_name() or request.user.username,
                },
            },
            settings.TALK_JWT_SECRET,
        )

    return result
