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
    limit = 1000

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
        # Ojo con el nombre del campo de fecha
        return published_non_satirical_articles.filter(date_published__gte=cutoff)
