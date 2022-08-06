# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from .views import memcached_status
from django.conf.urls import url

urlpatterns = [
    url(r'^status/$', memcached_status, name='memcached-status'),
]
