from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
def service_worker(request):
    return render(
        request,
        settings.PWA_SERVICE_WORKER_TEMPLATE,
        {'version': settings.PWA_SERVICE_WORKER_VERSION},
        content_type='application/javascript',
    )
