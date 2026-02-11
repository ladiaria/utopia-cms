# -*- coding: utf-8 -*-
# TODO: this module should be merged into __init__.py

from django.urls import re_path

from core.views.article import article_list


urlpatterns = [re_path(r'^(?P<type_slug>[\w-]+)/$', article_list, name='article_list')]
