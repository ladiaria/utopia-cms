# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

from core.views.supplement import supplement_list, supplement_download, supplement_email


urlpatterns = patterns('',
    url(r'^s/$', supplement_list, name='supplement_list'),
    url(
        r'^/(?P<supplement_slug>[\w-]+)/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        supplement_download,
        name='supplement_detail',
    ),
    url(r'^/email/$', supplement_email),
)
