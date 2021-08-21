# -*- coding: utf-8 -*-
from views import memcached_status
from django.conf.urls import url

urlpatterns = [
    url(r'^status/$', memcached_status, name='memcached-status'),
]
