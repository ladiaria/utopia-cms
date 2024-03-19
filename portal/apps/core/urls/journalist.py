# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

from core.views.journalist import journalist_detail


urlpatterns = [
    re_path(r'^(?P<journalist_slug>[\w-]+)/$', journalist_detail, name='journalist_detail'),
]
