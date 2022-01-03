# -*- coding: utf-8 -*-
from django.contrib.sitemaps import Sitemap

from core.models import Article
from . import NewsSitemap


class ArticleSitemap(Sitemap):
    changefreq = 'never'
    priority = 1.0
    protocol = 'https'
    limit = 1000

    def items(self):
        return Article.published.all()


class ArticleNewsSitemap(NewsSitemap):
    changefreq = 'never'
    priority = 1.0
    protocol = 'https'

    def items(self):
        return Article.published.all()
