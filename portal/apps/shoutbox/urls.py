# -*- coding: utf-8 -*-
from shoutbox.views import do_shout, shouts

from django.conf.urls.defaults import patterns, url, include

urlpatterns = patterns('',
    url(r'^$', do_shout, name='shout'),
    url(r'^list/$', shouts, name='shouts'),
)
