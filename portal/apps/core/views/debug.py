# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.http import HttpResponseForbidden
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required

from decorators import render_response


to_response = render_response('core/templates/debug/')


@never_cache
@to_response
def request_meta(request):
    # allow only admin users
    if not (getattr(settings, 'CORE_DEBUG_REQUEST_ALLOW_ALL', False) or request.user.is_superuser):
        return HttpResponseForbidden()
    return 'request_meta.html'


@never_cache
@to_response
@staff_member_required
def staff_only(request):
    return 'staff_only.html'


@never_cache
@to_response
@login_required
def auth_only(request):
    return 'auth_only.html'
