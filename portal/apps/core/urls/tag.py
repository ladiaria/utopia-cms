# -*- coding: utf-8 -*-

from django.urls import re_path

from core.views.tag import tag_detail


urlpatterns = [
    re_path(r'^(?P<tag_slug>[\w-]+)/$', tag_detail, name='tag_detail'),
]
