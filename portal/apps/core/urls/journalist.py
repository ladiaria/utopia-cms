# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from core.views.journalist import journalist_detail

from django.urls import re_path


urlpatterns = [

    re_path(
        r'^(?P<journalist_slug>[\w-]+)/$', journalist_detail,
        name='journalist_detail'),
    re_path(r'^(?P<journalist_slug>[\w-]+)/(?P<tag>[\w-]+)/$', journalist_detail,
        name='journalist_detail'),
]
