# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from core.views.journalist import journalist_detail

from django.conf.urls import url


urlpatterns = [

    url(
        r'^(?P<journalist_slug>[\w-]+)/$', journalist_detail,
        name='journalist_detail'),
    url(r'^(?P<journalist_slug>[\w-]+)/(?P<tag>[\w-]+)/$', journalist_detail,
        name='journalist_detail'),
]
