from django.conf import settings

from django_mobile import get_flavour, set_flavour
from django_mobile.conf import defaults


class OnlyArticleDetail(object):
    """ Middleware to customize AMP and overwrite django-mobile. """

    def process_request(self, request):
        if get_flavour(request) == 'amp':
            from django.core.urlresolvers import resolve
            current_url = resolve(request.path_info).url_name
            if current_url != 'article_detail':
                set_flavour('mobile', request, permanent=True)


class FlavoursCookieSecure(object):
    def process_response(self, request, response):
        flavours_cookie_key = getattr(settings, 'FLAVOURS_COOKIE_KEY', defaults.FLAVOURS_COOKIE_KEY)
        if flavours_cookie_key in response.cookies:
            response.cookies[flavours_cookie_key]['secure'] = settings.FLAVOURS_COOKIE_SECURE

        return response
