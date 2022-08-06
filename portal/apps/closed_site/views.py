from __future__ import unicode_literals

from django.template import Context, loader
from django.views.decorators.cache import never_cache

from closed_site import http


@never_cache
def temporary_unavailable(request, template_name='503.html'):
    t = loader.get_template(template_name)
    return http.HttpResponseTemporaryUnavailable(t.render(Context({})))
