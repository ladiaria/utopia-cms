from __future__ import unicode_literals
from builtins import object
from django.conf import settings
from django.urls import resolve, reverse
from django.http import HttpResponseRedirect
from django.contrib.sessions.models import Session


class SessionInvalidMiddleware(object):
    """
    Logout on invalid session (with user but no hash)
    WARNING: This was an attempt to redirect people when upgrading from Django 1.5 to 1.11 but didn't work very well,
             for example the URL redirect without trial slash may be broken if this middleware is set.
    """

    def process_request(self, request):
        redirect_url_name = 'account-invalid'
        if resolve(request.path_info).url_name != redirect_url_name:
            try:
                decoded = Session.objects.get(pk=request.COOKIES[settings.SESSION_COOKIE_NAME]).get_decoded()
                if '_auth_user_id' in decoded and '_auth_user_hash' not in decoded:
                    return HttpResponseRedirect(reverse(redirect_url_name))
            except (KeyError, Session.DoesNotExist):
                pass
