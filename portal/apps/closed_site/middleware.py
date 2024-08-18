# -*- coding: utf-8 -*-

import re

from django.conf import settings
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

from .views import temporary_unavailable


class ClosedSiteMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if getattr(settings, 'CLOSED_SITE', False):

            allowed_path_patterns = []
            allowed_paths = getattr(settings, 'CLOSED_SITE_ALLOWED_PATHS', ('^/media/.*', '^/admin/.*'))
            for path in allowed_paths:
                pattern = re.compile(path)
                allowed_path_patterns.append(pattern)

            user = getattr(request, 'user', False)
            if user and user.is_authenticated and user.is_staff:
                return None
            for pattern in allowed_path_patterns:
                if pattern.match(request.path):
                    return None
            return temporary_unavailable(request)


class RestrictedAccessMiddleware(MiddlewareMixin):
    """ This middleware requires a login for every view """

    def process_request(self, request):
        login_url = settings.LOGIN_URL
        admin_login = '/admin/'
        if request.path.startswith(getattr(settings, 'MEDIA_URL')):
            return None
        if getattr(settings, 'RESTRICT_ACCESS', False):
            if request.path != login_url and request.path != admin_login:
                if request.user.is_anonymous:
                    if request.POST:
                        return login(request, request.user)
                    else:
                        return HttpResponseRedirect(
                            '%(login_url)s?next=%(next)s' % {'login_url': login_url, 'next': request.path}
                        )
