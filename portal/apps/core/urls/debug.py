from django.conf.urls import patterns, url

from core.views.debug import request_meta, staff_only, auth_only


urlpatterns = patterns(
    '',
    url(r'^request-meta/$', request_meta),
    url(r'^staff-only/$', staff_only),
    url(r'^auth-only/$', auth_only),
)
