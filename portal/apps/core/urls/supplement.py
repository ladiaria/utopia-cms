# -*- coding: utf-8 -*-
from django.urls import path, re_path

from core.views.supplement import supplement_download, supplement_email


urlpatterns = [
    re_path(
        r'^(?P<supplement_slug>[\w-]+)/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        supplement_download,
        name='supplement_detail',
    ),
    path('email/', supplement_email),
]
