# -*- mode: python; coding: utf-8; -*-
from __future__ import unicode_literals

from builtins import object

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.urls import reverse, resolve, Resolver404
from urllib.parse import quote
from django.utils.deprecation import MiddlewareMixin


SSL = 'SSL'
SSL_HOST = settings.SITE_URL


class UrlMiddleware(MiddlewareMixin):
    """
    Middleware for removing the WWW from a URL if the users sets settings.REMOVE_WWW.
    Based on Django CommonMiddleware.
    """

    def process_request(self, request):
        host = request.get_host()
        old_url = [host, request.path]
        new_url = old_url[:]

        if settings.REMOVE_WWW and old_url[0] and old_url[0].startswith('www.'):
            new_url[0] = old_url[0][4:]

        if new_url != old_url:
            try:
                resolve(new_url[1])
            except Resolver404:
                pass
            else:
                if new_url[0]:
                    newurl = "%s://%s%s" % (
                        request.is_secure() and 'https' or 'http',
                        new_url[0],
                        quote(new_url[1]),
                    )
                else:
                    newurl = quote(new_url[1])
                if request.GET:
                    newurl += '?' + request.GET.urlencode()
                return HttpResponsePermanentRedirect(newurl)
        return None


class HttpsRedirectMiddleware(object):
    """
    Middleware for defining urls which should always be https.
    """

    def process_request(self, request):
        if settings.DEBUG:
            return None
        if hasattr(settings, 'SECURE_URLS'):
            secure_url = False
            for url in settings.SECURE_URLS:
                try:
                    if request.META.get('PATH_INFO') == reverse(url):
                        secure_url = True
                except Resolver404:
                    pass
            if not request.is_secure() and secure_url:
                return HttpResponsePermanentRedirect(
                    'https://%s%s' % (request.headers.get('host'), request.META.get('PATH_INFO'))
                )
            elif request.is_secure() and not secure_url:
                return HttpResponsePermanentRedirect(
                    'http://%s%s' % (request.headers.get('host'), request.META.get('PATH_INFO'))
                )
        return None


# http://www.djangosnippets.org/snippets/85/
class SSLRedirectMiddleware(object):
    """
    This middleware answers the problem of redirecting to (and from) a SSL
    secured path by stating what paths should be secured in urls.py file. To
    secure a path, add the additional view_kwarg 'SSL':True to the view_kwargs.

    For example:
        urlpatterns = patterns('some_site.some_app.views',
            (r'^test/secure/$','test_secure',{'SSL':True}),
        )

    All paths where 'SSL':False or where the kwarg of 'SSL' is not specified
    are routed to an unsecure path.

    For example:
        urlpatterns = patterns('some_site.some_app.views',
            (r'^test/unsecure1/$','test_unsecure',{'SSL':False}),
            (r'^test/unsecure2/$','test_unsecure'),
        )

    Gotcha's:
        Redirects should only occur during GETs; this is due to the fact that
        POST data will get lost in the redirect.

    Benefits/Reasoning:
        A major benefit of this approach is that it allows you to secure
        django.contrib views and generic views without having to modify the
        base code or wrapping the view.

        This method is also better than the two alternative approaches of
        adding to the settings file or using a decorator.

        It is better than the tactic of creating a list of paths to secure in
        the settings file, because you DRY. You are also not forced to
        consider all paths in a single location. Instead you can address the
        security of a path in the urls file that it is resolved in.

        It is better than the tactic of using a @secure or @unsecure
        decorator, because it prevents decorator build up on your view
        methods. Having a bunch of decorators makes views cumbersome to read
        and looks pretty redundant. Also because the all views pass through
        the middleware you can specify the only secure paths and the remaining
        paths can be assumed to be unsecure and handled by the middleware.

        This package is inspired by Antonio Cavedoni's SSL Middleware
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        if SSL in view_kwargs:
            secure = view_kwargs[SSL]
            del view_kwargs[SSL]
        else:
            secure = False

        if not settings.DEBUG:
            if not secure == self._is_secure(request):
                return self._redirect(request, secure)

        return None

    def _is_secure(self, request):
        if request.is_secure():
            return True

        # Trying to solve the https redirect loop in nginx
        if 'x-forwarded-protocol' in request.headers:
            return True
        # Handle the Webfaction case until this gets resolved in the request.is_secure()
        if 'x-forwarded-ssl' in request.headers:
            return request.headers['x-forwarded-ssl'] == 'on'

        return False

    def _redirect(self, request, secure):
        protocol = secure and "https" or "http"
        newurl = "%s://%s%s" % (protocol, SSL_HOST, request.get_full_path())
        if settings.DEBUG and request.method == 'POST':
            raise RuntimeError("Django can't perform a SSL redirect while ")
            "maintaining POST data. Please structure your views so that "
            "redirects only occur during GETs."

        return HttpResponsePermanentRedirect(newurl)
