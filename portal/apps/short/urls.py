# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.urls import path, re_path

from short.views import UrlDetailView
from core.views.article import ArticleDetailView
from short.views import redirect

urlpatterns = [
    # Short urls redirection view
    re_path(r'^url/(?P<url_id>\d+)/', redirect),

    # Per model short url view
    path('A/<int:pk>/', ArticleDetailView.as_view(template_name='url.html')),
    path('U/<int:pk>/', UrlDetailView.as_view(template_name='url.html')),
]
