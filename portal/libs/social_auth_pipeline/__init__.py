from django.http import HttpResponseRedirect

from thedaily.models import OAuthState
from thedaily.views import get_or_create_user_profile


def get_phone_number(backend, uid, user=None, social=None, *args, **kwargs):
    subscriber = get_or_create_user_profile(user)
    if not subscriber.phone:
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
