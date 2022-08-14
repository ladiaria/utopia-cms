from __future__ import unicode_literals
from core.views.breaking_news_module import notification_closed, content

from django.conf.urls import url

urlpatterns = [
    url(r'^(?P<bn_id>\d+)/closed/$', notification_closed, name='bn-notification-closed'),
    url(r'^content/$', content, name='bn-content'),
]
