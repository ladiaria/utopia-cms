from __future__ import unicode_literals
from django.urls import path

from notification.views import notice_settings


urlpatterns = [

    path("configuracion/", notice_settings, name="notification_notice_settings"),
]
