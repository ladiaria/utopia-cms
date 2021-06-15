# -*- coding: utf-8 -*-
from core.views.article import article_list

from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(r'^(?P<type_slug>[\w-]+)/$', article_list, name='article_list'),
)
