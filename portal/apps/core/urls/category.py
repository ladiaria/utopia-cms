# -*- coding: utf-8 -*-

from django.urls import re_path

from core.views.category import newsletter_preview, newsletter_browser_preview, nl_browser_authpreview


urlpatterns = [
    re_path(r'^(?P<slug>[\w-]+)/nl/$', newsletter_preview, name='category-nl-preview'),
    re_path(r'^(?P<slug>[\w-]+)/nl/browser-preview/$', nl_browser_authpreview, name='c-nl-browser-authpreview'),
    re_path(
        r'^(?P<slug>[\w-]+)/nl/(?P<hashed_id>\w+)/$', newsletter_browser_preview, name='category-nl-browser-preview'
    ),
]
