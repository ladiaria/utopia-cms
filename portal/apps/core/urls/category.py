# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from core.views.category import newsletter_preview, newsletter_browser_preview


urlpatterns = [
    url(r'^(?P<slug>\w+)/nl/$', newsletter_preview, name='category-nl-preview'),
    url(r'^(?P<slug>\w+)/nl/(?P<hashed_id>\w+)/$', newsletter_browser_preview, name='category-nl-browser-preview'),
]
