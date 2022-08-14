# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from builtins import object
from django.conf import settings
from django.conf.urls import defaults
from django.contrib.auth.views import login
from django.core import urlresolvers
from django.http import HttpResponseRedirect

import re

defaults.handler503 = 'closed_site.views.temporary_unavailable'
defaults.__all__.append('handler503')
CLOSED_SITE_ALLOWED_PATHS = ('^/media/.*', '^/admin/.*')


class ClosedSiteMiddleware(object):
    def __init__(self):
        self.allowed_path_patterns = []
        allowed_paths = getattr(settings, 'CLOSED_SITE_ALLOWED_PATHS',
                                CLOSED_SITE_ALLOWED_PATHS)
        for path in allowed_paths:
            pattern = re.compile(path)
            self.allowed_path_patterns.append(pattern)

    def process_request(self, request):
        if getattr(settings, 'CLOSED_SITE', False):
            user = getattr(request, 'user', False)
            if user and user.is_authenticated() and user.is_staff:
                return None
            for pattern in self.allowed_path_patterns:
                if pattern.match(request.path):
                    return None
            resolver = urlresolvers.get_resolver(None)
            callback, param_dict = resolver._resolve_special('503')
            return callback(request, **param_dict)


class RestrictedAccessMiddleware(object):
    """This middleware requires a login for every view"""
    def process_request(self, request):
        login_url = getattr(settings, 'RESTRICT_ACCESS_LOGIN_URL',
                            getattr(settings, 'LOGIN_URL'))
        admin_login = '/admin/'
        if request.path.startswith(getattr(settings, 'MEDIA_URL')):
            return None
        if getattr(settings, 'RESTRICT_ACCESS', False):
            if request.path != login_url and request.path != admin_login:
                if request.user.is_anonymous():
                    if request.POST:
                        return login(request)
                    else:
                        return HttpResponseRedirect('%(login_url)s?next=%(next)s' % \
                            {'login_url': login_url, 'next': request.path})
