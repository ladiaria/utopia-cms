import logging
from social_core.exceptions import AuthException

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User

from thedaily.models import OAuthState
from thedaily.utils import get_or_create_user_profile, subscribe_log

USER_FIELDS = ["username", "email"]


def create_user_inactive(strategy, details, backend, user=None, *args, **kwargs):
    """
    Create user with is_active=False for new Google OAuth users.
    They will be activated after SMS verification.
    """
    if user:
        return {"is_new": False}

    fields = {
        name: kwargs.get(name, details.get(name))
        for name in backend.setting("USER_FIELDS", USER_FIELDS)
    }
    if not fields:
        return

    # Create user with is_active=False
    fields['is_active'] = False

    return {"is_new": True, "user": strategy.create_user(**fields)}


class AuthIntegrityError(AuthException):
    def __str__(self):
        return "El email de la cuenta de Google utilizada ya está siendo usado por otro usuario."


def check_email_in_use(backend, details, uid, user=None, *args, **kwargs):
    """
    Taken from https://stackoverflow.com/a/40631405/2292933 and modified by us.
    Avoid associate an email already in use by another user.
    """
    email = details.get('email')
    if user:
        # logged-in assoc, check by username and email excluding the logged in user
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exclude(id=user.id).exists():
            raise AuthIntegrityError(backend)
    elif User.objects.filter(username__iexact=email).exclude(email__iexact=email).exists():
        # a new assoc, username with the email should not exist (unless is the one who has that email)
        raise AuthIntegrityError(backend)


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

    # Add default newsletters and populate name data for new Google users
    if is_new:
        from utopia_cms_ladiaria.utils import add_default_newsletters_for_new_user

        request = kwargs.get('request')
        details = kwargs.get('details', {})

        if request:
            subscribe_log(request, f'Adding default newsletters for new Google user: {user.email}')

        # Populate first_name and last_name from Google data
        try:
            first_name = details.get('first_name', '').strip()
            last_name = details.get('last_name', '').strip()

            # If first/last name not available, try to split fullname
            if not first_name and not last_name:
                fullname = details.get('fullname') or details.get('full_name', '')
                if fullname:
                    name_parts = fullname.strip().split(' ', 1)
                    first_name = name_parts[0] if name_parts else ''
                    last_name = name_parts[1] if len(name_parts) > 1 else ''

            # Update user's name fields if we have the data
            if first_name or last_name:
                user.first_name = first_name
                user.last_name = last_name
                user.save()

                if request:
                    subscribe_log(request, f'Updated name for Google user {user.email}: {first_name} {last_name}')

        except Exception as exc:
            if request:
                subscribe_log(request, f'Error updating name for Google user {user.email}: {exc}')
            # Don't fail the login process if name update fails

        # Add default newsletters using centralized function
        try:
            add_default_newsletters_for_new_user(subscriber, extra_category=None)

            if request:
                subscribe_log(request, f'Default newsletters added successfully. User: {user.email}')
        except Exception as exc:
            if request:
                subscribe_log(request, f'Error adding newsletters for new Google user {user.email}: {exc}')
            # Don't fail the login process if newsletters fail
    # The "missing data" form is shown when any of the following conditions is met:
    # 1. This is a new user and the user has no phone number and the phone number is required by settings.
    # 2. This is an existing user but inactive (missing phone number) - CASO 1: CUENTA NO ACTIVA
    # 3. T&C are configured, assumed not to be accepted by default in google and the user has not accepted them yet.
    if (
        (settings.THEDAILY_GOOGLE_OAUTH2_ASK_PHONE and not subscriber.phone and is_new)
        or (settings.THEDAILY_GOOGLE_OAUTH2_ASK_PHONE and not subscriber.phone and not user.is_active)  # CASO 1
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
                OAuthState.objects.create(user=user, state=state, fullname=kwargs['details'].get('fullname'))
        return HttpResponseRedirect('/usuarios/registrate/?step=2&google_flow=1&state=%s%s' % (state, '&is_new=1' if is_new else ""))
