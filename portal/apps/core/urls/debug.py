from __future__ import unicode_literals
from django.urls import path

from core.views.debug import request_meta, staff_only, auth_only


urlpatterns = [
    path('request-meta/', request_meta),
    path('staff-only/', staff_only),
    path('auth-only/', auth_only),
]
