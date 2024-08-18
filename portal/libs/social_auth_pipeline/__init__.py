
from social_core.exceptions import AuthException

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User

from thedaily.models import OAuthState
from thedaily.views import get_or_create_user_profile


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
    subscriber = get_or_create_user_profile(user)
    if not subscriber.phone or (
        settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID and not subscriber.terms_and_conds_accepted
    ):
        state = kwargs['request'].GET['state']
        try:
            oas = OAuthState.objects.get(user=user)
            oas.state = state
            oas.save()
        except OAuthState.DoesNotExist:
            OAuthState.objects.create(user=user, state=state, fullname=kwargs['details'].get('fullname'))
        is_new, query_params = kwargs.get('is_new'), ''
        if is_new:
            query_params = '?is_new=1'
        return HttpResponseRedirect('/usuarios/registrate/google/' + query_params)
