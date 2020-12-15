from django.http import HttpResponseRedirect

from thedaily.models import OAuthState
from thedaily.views import get_or_create_user_profile


def get_phone_number(backend, uid, user=None, social=None, *args, **kwargs):
    subscriber = get_or_create_user_profile(user)
    if not subscriber.phone:
        state = kwargs['request']['state']
        try:
            oas = OAuthState.objects.get(user=user)
            oas.state = state
            oas.save()
        except OAuthState.DoesNotExist:
            OAuthState.objects.create(
                user=user, state=state,
                fullname=kwargs['details'].get('fullname'))
        return HttpResponseRedirect(
            '/usuarios/registrate/google/' + (
                '?is_new=1' if kwargs.get('is_new') else ''))
