import logging
from social_core.exceptions import AuthException

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User

from thedaily.models import OAuthState
from thedaily.utils import get_or_create_user_profile, subscribe_log


class AuthIntegrityError(AuthException):
    def __str__(self):
        return "El email de la cuenta de Google utilizada ya está siendo usado por otro usuario."


def check_email_in_use(backend, details, uid, user=None, *args, **kwargs):
    """
    Taken from https://stackoverflow.com/a/40631405/2292933 and modified by us.
    Avoid associate an email already in use by another user.
    """
    email, error_exception_obj = details.get('email'), AuthIntegrityError(backend)
    if user:
        # logged-in assoc, check by username and email excluding the logged in user
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exclude(id=user.id).exists():
            raise error_exception_obj
    elif User.objects.filter(username__iexact=email).exclude(email__iexact=email).exists():
        # a new assoc, username with the email should not exist (unless is the one who has that email)
        raise error_exception_obj


def get_phone_number(backend, uid, user=None, social=None, *args, **kwargs):
    """
    TODO: This pipeline should be migrated to a "partial" approach, examples in
          https://github.com/python-social-auth/social-examples/blob/master/example-common/pipeline.py
          Because the redirect returned here can destroy the session (*), and also the user will be still created and
          validated but without the data we are asking for (the purpose of this pipeline).
          (*) To face this "session removal" we set the session's modified attr to True in some parts of our code, but
              this doesn't seem to be the right way, we believe that the "partial" approach is the right solution.
    """
    subscriber, is_new = get_or_create_user_profile(user), kwargs.get('is_new')
    # The "missing data" form is shown when any of the following conditions is met:
    # 1. This is a new user and the user has no phone number and the phone number is required by settings.
    # 2. T&C are configured, assumed not to be accepted by default in google and the user has not accepted them yet.
    if (
        (settings.THEDAILY_GOOGLE_OAUTH2_ASK_PHONE and subscriber.phone == "" and is_new)
        or (settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID and not subscriber.terms_and_conds_accepted)
    ):
        request = kwargs['request']
        state = request.GET['state']
        try:
            oas = OAuthState.objects.get(user=user)
            if oas.phone_submitted_blank:
                oas.delete()
                return
            else:
                oas.state = state
                if is_new:
                    oas.is_new = True
                oas.save()
        except OAuthState.DoesNotExist:
            by_state = OAuthState.objects.filter(state=state)
            if by_state.exists():
                # TODO: (doing) we're debugging scenarios when the state already exists, but the user is not the same.
                #       After debugging, this comment should be replaced with a more suitable one.
                #       TODO: Log also the collector_analysis of the user saved in the OAuthState, perhaps we can
                #             replace with the user received here.
                msg = (
                    "A creation of an OAuthState with different user and already existing state was aborted: state "
                    f"received='{state}', user received='{user}'"
                )
                subscribe_log(request, msg, logging.DEBUG)
                return HttpResponseRedirect(reverse("login-error"))
            else:
                oasnew = OAuthState.objects.create(
                    user=user, state=state, fullname=kwargs['details'].get('fullname'), is_new=is_new
                )
                subscribe_log(request, f'OAuthState created: {oasnew} for user {user}')
        return HttpResponseRedirect('/usuarios/registrate/google/%s' % ('?is_new=1' if is_new else ""))
