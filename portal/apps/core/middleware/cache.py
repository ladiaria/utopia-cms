from django.conf import settings
from django.core.cache import cache
from django.urls import resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin
from django.utils.cache import get_cache_key
from django.utils.timezone import now


debug_cache = getattr(settings, 'HOME_CACHE_DEBUG', False)


class AnonymousRequest(MiddlewareMixin):
    anon_request_url_names_include_auth = getattr(settings, 'PORTAL_ANON_REQUEST_URL_NAMES_INCLUDE_AUTH', [])

    def process_request(self, request):
        """
        set cookies headers to None if anon user and home-page or (article_detail when signupwall is disabled) or
        url_name resolved is included in PORTAL_ANON_REQUEST_URL_NAMES_INCLUDE_AUTH (even if user is authenticated).

        (to make the same page cache fetch for all anon users)
        """
        if debug_cache and request.path == '/':
            print(
                "DEBUG: cache.process_request: anon=%s, COOKIE header=%s, session_key=%s"
                % (
                    request.user.is_anonymous,
                    request.headers.get('cookie'),
                    request.COOKIES.get(settings.SESSION_COOKIE_NAME),
                )
            )
        if hasattr(request, 'user'):
            clear, url_name_resolved = False, None
            if not request.user.is_authenticated:
                clear = request.path == '/'
                if not (clear or settings.SIGNUPWALL_ENABLED):
                    url_name_resolved = resolve(request.path_info).url_name
                    clear = url_name_resolved == 'article_detail'
            if not clear:
                url_name_resolved = url_name_resolved or resolve(request.path_info).url_name
                clear = url_name_resolved in AnonymousRequest.anon_request_url_names_include_auth
            if clear:
                request.META['HTTP_COOKIE'] = None
                request.META['HTTP_ACCEPT_ENCODING'] = 'identity'
            if debug_cache:
                GREEN = '\033[92m'
                WARNC = '\033[93m'  # Yellow
                ENDC = '\033[0m'  # Reset color
                cache_state = f"{GREEN} cache HIT" if cache.get(get_cache_key(request)) else f"{WARNC} cache MISS"
                print(
                    f"[{now().strftime('%Y-%m-%d %H:%M:%S')}] DEBUG: {cache_state}{ENDC}: ({url_name_resolved}) "
                    f"{request.path}"
                )


class AnonymousResponse(MiddlewareMixin):
    def process_response(self, request, response):
        """
        idem as above (to make the page cache not be updated)
        """
        if response.status_code in [404, 301, 302]:
            if debug_cache:
                print(f"DEBUG: cache.process_response(begin): {response.status_code}: {request.path}")
            return response
        if debug_cache and request.path == '/':
            print(
                "DEBUG: cache.process_response: anon=%s, COOKIE header=%s, session_key=%s"
                % (
                    request.user.is_anonymous,
                    request.headers.get('cookie'),
                    request.COOKIES.get(settings.SESSION_COOKIE_NAME),
                )
            )
        if hasattr(request, 'user'):
            clear, url_name_resolved = False, None
            if not request.user.is_authenticated:
                clear = request.path == '/'
                if not (clear or settings.SIGNUPWALL_ENABLED):
                    # TODO: maybe a try-except is not neccesary if we have the response status code (only if 200?)
                    try:
                        url_name_resolved = resolve(request.path_info).url_name
                        clear = url_name_resolved == 'article_detail'
                    except Resolver404:
                        pass
            if not clear:
                url_name_resolved = url_name_resolved or resolve(request.path_info).url_name
                clear = url_name_resolved in AnonymousRequest.anon_request_url_names_include_auth
            if clear:
                request.META['HTTP_COOKIE'] = None
                request.META['HTTP_ACCEPT_ENCODING'] = 'identity'
        if debug_cache:
            print(f"DEBUG: cache.process_response(end): {response.status_code}: {request.path}")
        return response
