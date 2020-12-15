# -*- coding: utf-8 -*-
from core.views.category import newsletter_preview

from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('', url(r'^(?P<slug>\w+)/nl/$', newsletter_preview, name='category-nl-preview'))
