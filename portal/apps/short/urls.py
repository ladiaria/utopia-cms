# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

from short.views import UrlDetailView
from core.views.article import ArticleDetailView
from core.models import Article
from short.models import Url

urlpatterns = patterns(
    'short.views',
    # Short urls redirection view
    url(r'^url/(?P<url_id>\d+)/', 'redirect'),

    # Per model short url view
    url(r'^A/(?P<pk>\d+)/$', ArticleDetailView.as_view(template_name='url.html')),
    url(r'^U/(?P<pk>\d+)/$', UrlDetailView.as_view(template_name='url.html')),
)
