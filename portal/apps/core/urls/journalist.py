# -*- coding: utf-8 -*-
from core.views.journalist import journalist_detail

from django.conf.urls import patterns, url


urlpatterns = patterns(
    '',
    url(
        r'^(?P<journalist_slug>[\w-]+)/$', journalist_detail,
        name='journalist_detail'),
    url(r'^(?P<journalist_slug>[\w-]+)/(?P<tag>[\w-]+)/$', journalist_detail,
        name='journalist_detail'),
)
