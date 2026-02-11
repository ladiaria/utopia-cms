from django.urls import path
from django.conf import settings

from core.views.debug import request_meta, staff_only, auth_only, session_popkey, debug_custom_handlers


urlpatterns = [
    path('request-meta/', request_meta),
    path('staff-only/', staff_only),
    path('auth-only/', auth_only),
    path('session-popkey/<str:key>/', session_popkey),
]

if getattr(settings, 'DEBUG_CUSTOM_HANDLERS', False):
    urlpatterns.append(path('handler/<int:status>/', debug_custom_handlers))
