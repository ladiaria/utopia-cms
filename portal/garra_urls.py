from django.conf.urls.defaults import url, patterns
from django.views.generic import RedirectView

from urls import urlpatterns as default_patterns

urlpatterns = default_patterns + patterns(
    '',
    url(r'^[Rr]usia-?2018/$',
        RedirectView.as_view(url='/seccion/rusia-2018/')), )
