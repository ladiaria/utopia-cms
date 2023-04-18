# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from shoutbox.views import do_shout, shouts

from django.urls import path

urlpatterns = [
    path('', do_shout, name='shout'),
    path('list/', shouts, name='shouts'),
]
