# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404

from core.models import Article, get_current_edition, get_current_feeds, Journalist, Section, Supplement, Edition
from core.templatetags.ldml import ldmarkup, cleanhtml


site = Site.objects.get_current()


class LatestArticles(Feed):
    title = site.name
    link = '/'
    description = u'Artículos de la publicación periodística %s.' % site.name

    def items(self):
        item_list = get_current_feeds()
        return item_list

    def item_title(self, item):
        return cleanhtml(ldmarkup(item.headline))

    def item_description(self, item):
        deck = "<h2>%s</h2><br/>" % ldmarkup(item.deck) if item.deck else ""
        return "%s" % deck + ldmarkup(item.body[:400] + "...") + "<a href='%s://%s%s'>Continuar leyendo...</a>" % (
            settings.URL_SCHEME, settings.SITE_DOMAIN, item.get_absolute_url())

    def item_pubdate(self, item):
        return item.date_published

    def item_author_name(self, item):
        if item.get_authors():
            return item.get_authors()[0]
        else:
            return ""

    def item_categories(self, item):
        return [item.get_sections()]


class LatestArticlesByCategory(Feed):
    link = '/'

    def get_object(self, *args, **kwargs):
        return get_object_or_404(Section, slug=kwargs.get('section_slug'))

    def title(self, obj):
        return u'%s - %s' % (site.name, obj.name)

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return u'Artículos de la sección "%s" de %s.' % (obj.name, site.name)

    def items(self, obj):
        return obj.latest_articles()


class LatestEditions(Feed):
    title = u'%s - Ediciones' % site.name
    link = '/'
    description = u'Ediciones de la publicación periodística %s.' % site.name

    def items(self):
        edition = get_current_edition()
        return Edition.objects.filter(id__lte=edition.id)[:10]


class LatestSupplements(Feed):
    title = u'%s - Suplementos' % site.name
    link = '/'
    description = u'Suplementos de la publicación periodística %s.' % site.name

    def items(self):
        edition = get_current_edition()
        return Supplement.objects.filter(edition__id__lte=edition.id, public=True)[:10]


class ArticlesByJournalist(Feed):
    link = '/'

    def title(self, obj):
        return u'%s - %s' % (site.name, obj.name)

    def get_object(self, *args, **kwargs):
        return get_object_or_404(Journalist, slug=kwargs.get('journalist_slug'))

    def description(self, obj):
        return u'Artículos escritos por %s' % obj.name

    def items(self, obj):
        return Article.objects.filter(byline=obj, is_published=True).order_by('-date_published')[:10]

    def item_link(self, obj):
        return obj.get_absolute_url()

    def item_pubdate(self, obj):
        return obj.date_published
