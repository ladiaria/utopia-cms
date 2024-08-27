# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.sitemaps import Sitemap

from core.models import Article
from . import NewsSitemap


published_non_satirical_articles = Article.published.exclude(
    sections__slug__in=getattr(settings, 'CORE_SATIRICAL_SECTIONS', ())
)


class ArticleSitemap(Sitemap):
    changefreq = 'never'
    priority = 1.0
    protocol = 'https'
    limit = 1000

    def items(self):
        return published_non_satirical_articles


class ArticleNewsSitemap(NewsSitemap):
    changefreq = 'never'
    priority = 1.0
    protocol = 'https'

    def items(self):
        return published_non_satirical_articles
