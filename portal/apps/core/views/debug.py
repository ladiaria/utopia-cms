# -*- coding: utf-8 -*-
from pydoc import locate
from django_user_agents.utils import get_user_agent

from django.conf import settings
from django.http import JsonResponse, Http404
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.defaults import page_not_found

from decorators import render_response
from urls import handler404 as custom_404_handler
from closed_site.views import temporary_unavailable
from homev3.views import custom_500_handler


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


@never_cache
def debug_custom_handlers(request, status):
    """
    This view is used to test custom handlers
    """
    if status == 403:
        raise PermissionDenied
    elif status == 500:
        if settings.DEBUG:
            return custom_500_handler(request)
        else:
            raise Exception("raised from debug_custom_handlers")
    elif status == 503:
        return temporary_unavailable(request)
    if settings.DEBUG:
        if custom_404_handler:
            return locate(custom_404_handler)(request, Http404)
        else:
            return page_not_found(request, Http404("called from debug_custom_handlers"))
    else:
        raise Http404
