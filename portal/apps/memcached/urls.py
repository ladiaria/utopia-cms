# -*- coding: utf-8 -*-
from views import memcached_status
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^status/$', memcached_status, name='memcached-status'),
)
