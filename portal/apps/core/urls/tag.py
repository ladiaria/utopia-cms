# -*- coding: utf-8 -*-
from core.views.tag import tag_detail

from django.conf.urls.defaults import patterns, url


urlpatterns = patterns(
    '',
    url(r'^(?P<tag_slug>[\w-]+)/$', tag_detail, name='tag_detail'),
)
