# -*- coding: utf-8 -*-
from core.views.category import newsletter_preview

from django.conf.urls import url

urlpatterns = [
    url(r'^(?P<slug>\w+)/nl/$', newsletter_preview, name='category-nl-preview')
]
