# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from search.views import search

urlpatterns = patterns('',
    url(r'^$', search, name='search'),
    url(r'^(?P<token>.+)/$', search, name='search_terms'),
)
