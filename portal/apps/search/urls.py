# -*- coding: utf-8 -*-
from django.urls import re_path
from search.views import search

urlpatterns = [
    re_path(r'^$', search, name='search'),
    re_path(r'^(?P<token>.+)/$', search, name='search_terms'),
]
