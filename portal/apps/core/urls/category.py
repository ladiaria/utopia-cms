# -*- coding: utf-8 -*-
from core.views.category import newsletter_preview, newsletter_browser_preview

from django.conf.urls import url

urlpatterns = [
    url(r'^(?P<slug>\w+)/nl/$', newsletter_preview, name='category-nl-preview'),
    url(r'^(?P<slug>\w+)/nl/(?P<hashed_id>\w+)/$', newsletter_browser_preview, name='category-nl-browser-preview'),
]
