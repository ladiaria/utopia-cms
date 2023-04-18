# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from .views import calendar, day_detail, event_detail

from django.urls import path, re_path


urlpatterns = [
    path('', calendar, name='events-calendar'),
    re_path(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/$', calendar, name='events-calendar'),
    re_path(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', day_detail, name='events-day_detail'),
    re_path(
        r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<event_slug>[\w-]+)/$',
        event_detail,
        name='events-event_detail',
    ),
]
