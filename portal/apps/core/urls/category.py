# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

from core.views.category import newsletter_preview, newsletter_browser_preview


urlpatterns = [
    re_path(r'^(?P<slug>\w+)/nl/$', newsletter_preview, name='category-nl-preview'),
    re_path(r'^(?P<slug>\w+)/nl/(?P<hashed_id>\w+)/$', newsletter_browser_preview, name='category-nl-browser-preview'),
]
