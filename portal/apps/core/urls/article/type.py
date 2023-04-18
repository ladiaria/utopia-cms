# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from core.views.article import article_list

from django.urls import re_path


urlpatterns = [re_path(r'^(?P<type_slug>[\w-]+)/$', article_list, name='article_list')]
