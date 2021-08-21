from django.conf.urls import url

from notification.views import notice_settings


urlpatterns = [

    url(r"^configuracion/$", notice_settings, name="notification_notice_settings"),
]
