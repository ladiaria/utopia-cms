
from django.conf import settings
from django.template import loader
from django.views.decorators.cache import never_cache

from closed_site import http


@never_cache
def temporary_unavailable(request, template_name=getattr(settings, "CLOSED_SITE_503_TEMPLATE", '503.html')):
    t = loader.get_template(template_name)
    return http.HttpResponseTemporaryUnavailable(t.render({}))
