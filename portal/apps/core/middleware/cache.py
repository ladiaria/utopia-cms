
from django.conf import settings
from django.urls import resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin


class AnonymousRequest(MiddlewareMixin):
    def process_request(self, request):
        """
        set cookies headers to None if anon user and home-page or (article_detail when signupwall is disabled)
        (to make the same page cache fetch for all anon users)
        """
        if getattr(settings, 'HOME_CACHE_DEBUG', False) and request.path == '/':
            print(
                "DEBUG: cache.process_request: anon=%s, COOKIE header=%s, session_key=%s"
                % (
                    request.user.is_anonymous,
                    request.headers.get('cookie'),
                    request.COOKIES.get(settings.SESSION_COOKIE_NAME),
                )
            )
        if hasattr(request, 'user') and not request.user.is_authenticated:
            clear = request.path == '/'
            if not (clear or settings.SIGNUPWALL_ENABLED):
                clear = resolve(request.path_info).url_name == 'article_detail'
            if clear:
                request.META['HTTP_COOKIE'] = None


class AnonymousResponse(MiddlewareMixin):
    def process_response(self, request, response):
        """ idem as above (to make the page cache not be updated) """
        if getattr(settings, 'HOME_CACHE_DEBUG', False) and request.path == '/':
            print(
                "DEBUG: cache.process_response: anon=%s, COOKIE header=%s, session_key=%s"
                % (
                    request.user.is_anonymous,
                    request.headers.get('cookie'),
                    request.COOKIES.get(settings.SESSION_COOKIE_NAME),
                )
            )
        if hasattr(request, 'user') and not request.user.is_authenticated:
            clear = request.path == '/'
            if not (clear or settings.SIGNUPWALL_ENABLED):
                # TODO: maybe a try-except is not neccesary if we have the response status code
                try:
                    clear = resolve(request.path_info).url_name == 'article_detail'
                except Resolver404:
                    pass
            if clear:
                request.META['HTTP_COOKIE'] = None
        return response
