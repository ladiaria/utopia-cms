from __future__ import unicode_literals

from django.http import HttpResponseRedirect

from thedaily.models import OAuthState
from thedaily.views import get_or_create_user_profile


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
