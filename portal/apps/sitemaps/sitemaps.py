# -*- coding: utf-8 -*-
from datetime import timedelta

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.utils import timezone

from core.models import Article
from . import NewsSitemap, NewsSitemap48hs


published_non_satirical_articles = Article.published.exclude(
    sections__slug__in=getattr(settings, 'CORE_SATIRICAL_SECTIONS', ())
)


class ArticleSitemap(Sitemap):
    changefreq = 'never'
    priority = 1.0
    protocol = 'https'
    # This is the general (web) sitemap, so Google's per-sitemap limit is 50000
    # URLs (not the 1000 of Google News). Paginating by 1000 produced ~140
    # pages, each a separate cache key that crawlers hit one by one, defeating
    # the cache. A high limit keeps it to a handful of pages. The Google News
    # sitemaps (ArticleNewsSitemap, ArticleNews48hsSitemap) keep limit=1000.
    limit = 50000

    def items(self):
        return published_non_satirical_articles


class ArticleNewsSitemap(NewsSitemap):
    changefreq = 'never'
    priority = 1.0
    protocol = 'https'

    def items(self):
        return published_non_satirical_articles


class ArticleNews48hsSitemap(NewsSitemap48hs):
    protocol = 'https'

    def items(self):
        cutoff = timezone.now() - timedelta(hours=48)

        return published_non_satirical_articles.filter(date_published__gte=cutoff)
