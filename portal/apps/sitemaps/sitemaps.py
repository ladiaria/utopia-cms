# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.contrib.sitemaps import Sitemap

from core.models import Article
from . import NewsSitemap


class ArticleSitemap(Sitemap):
    changefreq = 'never'
    priority = 1.0
    protocol = 'https'
    limit = 1000

    def items(self):
        return Article.objects.filter(is_published=True, date_published__lte=datetime.now())


class ArticleNewsSitemap(NewsSitemap):
    changefreq = 'never'
    priority = 1.0
    protocol = 'https'

    def items(self):
        return Article.objects.filter(
            is_published=True, date_published__lte=datetime.now()).order_by('-date_published')
