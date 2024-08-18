from django.urls import path

from core.views.debug import request_meta, staff_only, auth_only, session_popkey


urlpatterns = [
    path('request-meta/', request_meta),
    path('staff-only/', staff_only),
    path('auth-only/', auth_only),
    path('session-popkey/<str:key>/', session_popkey),
]
