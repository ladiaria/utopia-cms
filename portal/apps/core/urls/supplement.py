# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf.urls import url

from core.views.supplement import supplement_download, supplement_email


urlpatterns = [
    url(
        r'^(?P<supplement_slug>[\w-]+)/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        supplement_download,
        name='supplement_detail',
    ),
    url(r'^email/$', supplement_email),
]
