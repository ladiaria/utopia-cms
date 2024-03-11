# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django_user_agents.utils import get_user_agent

from django.conf import settings
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
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
        raise PermissionDenied
    return 'request_meta.html', {"is_mobile": get_user_agent(request).is_mobile}


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


@never_cache
@login_required
def session_popkey(request, key):
    """
    Removes a key from the user session
    """
    request.session.pop(key, None)
    return JsonResponse({"status": "key was removed"})
