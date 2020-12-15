from django.conf.urls import patterns, url

from notification.views import notice_settings


urlpatterns = patterns(
    "",
    url(r"^configuracion/$", notice_settings, name="notification_notice_settings"),
)
