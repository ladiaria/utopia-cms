# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from shoutbox.views import do_shout, shouts

from django.conf.urls import url, include

urlpatterns = [
    url(r'^$', do_shout, name='shout'),
    url(r'^list/$', shouts, name='shouts'),
]
