# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Rss201rev2Feed

from libs.utils import get_site_name
from core.models import Article, get_current_edition, get_current_feeds, Journalist, Section, Supplement, Edition
from core.templatetags.ldml import ldmarkup, cleanhtml


site_name = get_site_name()


class MinimalImageRSSFeed(Rss201rev2Feed):
    def rss_attributes(self):
        attrs = super().rss_attributes()
        attrs.update({
            'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'xmlns:content': 'http://purl.org/rss/1.0/modules/content/',
            'xmlns:atom': 'http://www.w3.org/2005/Atom',
            'xmlns:media': 'http://search.yahoo.com/mrss/',
            'xmlns:image': 'http://www.google.com/schemas/sitemap-image/1.1',
        })
        return attrs

    def add_item_elements(self, handler, item):
        super().add_item_elements(handler, item)

        image_url = item.get('image_url')
        if image_url:
            handler.startElement('image:image', {})
            handler.addQuickElement('image:loc', image_url)
            image_title = item.get('image_title')
            if image_title:
                handler.startElement('image:title', {})
                handler._write('<![CDATA[' + str(image_title) + ']]>')
                handler.endElement('image:title')
            handler.endElement('image:image')

        categories = item.get('categories_cdata') or []
        for cat in categories:
            if not cat:
                continue
            handler.startElement('category', {})
            handler._write('<![CDATA[' + str(cat) + ']]>')
            handler.endElement('category')


class LatestArticles(Feed):
    feed_type = MinimalImageRSSFeed
    title = site_name
    link = '/'
    description = u'Artículos de la publicación periodística %s.' % site_name
    item_guid_is_permalink = False

    def feed_url(self):
        return f"{settings.URL_SCHEME}://{settings.SITE_DOMAIN}/feeds/articulos/"

    def item_guid(self, item):
        return u'%s.%d' % (settings.SITE_DOMAIN, item.id)

    def items(self):
        return get_current_feeds()

    def item_title(self, item):
        return cleanhtml(ldmarkup(item.headline))

    def item_description(self, item):
        deck = "<h2>%s</h2><br/>" % ldmarkup(item.deck) if item.deck else ""
        return "%s" % deck + ldmarkup(item.body[:400] + "...") + '<a href="%s://%s%s">Continuar leyendo...</a>' % (
            settings.URL_SCHEME, settings.SITE_DOMAIN, item.get_absolute_url()
        )

    def item_pubdate(self, item):
        return item.date_published

    def item_categories(self, item):
        return []

    def item_link(self, item):
        return f"{settings.URL_SCHEME}://{settings.SITE_DOMAIN}{item.get_absolute_url()}"

    def item_extra_kwargs(self, item):
        image_url = None
        image_title = getattr(item, 'photo_caption', None)
        photo = getattr(item, 'photo', None)
        if photo:
            get_1440 = getattr(photo, 'get_1440w_url', None)
            get_700 = getattr(photo, 'get_700w_url', None)
            if callable(get_1440):
                image_url = get_1440()
            elif callable(get_700):
                image_url = get_700()
            else:
                image_url = getattr(photo, 'url', None)

        sections = item.get_sections()
        if hasattr(sections, 'values_list'):
            categories_cdata = list(sections.values_list('name', flat=True))
        elif isinstance(sections, (list, tuple, set)):
            categories_cdata = [str(s) for s in sections]
        elif isinstance(sections, str):
            categories_cdata = [p.strip() for p in sections.split(',') if p.strip()]
        else:
            categories_cdata = [str(sections)] if sections else []

        return {
            'image_url': image_url,
            'image_title': image_title,
            'categories_cdata': categories_cdata,
        }


class LatestArticlesByCategory(Feed):
    link = '/'

    def get_object(self, *args, **kwargs):
        return get_object_or_404(Section, slug=kwargs.get('section_slug'))

    def title(self, obj):
        return u'%s - %s' % (site_name, obj.name)

    def link(self, obj):  # noqa
        # TODO: redefined (fix)
        return obj.get_absolute_url()

    def description(self, obj):
        return u'Artículos de la sección "%s" de %s.' % (obj.name, site_name)

    def items(self, obj):
        return obj.latest_articles()


class LatestEditions(Feed):
    title = u'%s - Ediciones' % site_name
    link = '/'
    description = u'Ediciones de la publicación periodística %s.' % site_name

    def items(self):
        edition = get_current_edition()
        return Edition.objects.filter(id__lte=edition.id)[:10]


class LatestSupplements(Feed):
    title = u'%s - Suplementos' % site_name
    link = '/'
    description = u'Suplementos de la publicación periodística %s.' % site_name

    def items(self):
        edition = get_current_edition()
        return Supplement.objects.filter(edition__id__lte=edition.id, public=True)[:10]


class ArticlesByJournalist(Feed):
    link = '/'

    def title(self, obj):
        return u'%s - %s' % (site_name, obj.name)

    def get_object(self, *args, **kwargs):
        return get_object_or_404(Journalist, slug=kwargs.get('journalist_slug'))

    def description(self, obj):
        return u'Artículos escritos por %s' % obj.name

    def items(self, obj):
        return Article.published.filter(byline=obj)[:10]

    def item_link(self, obj):
        return obj.get_absolute_url()

    def item_pubdate(self, obj):
        return obj.date_published
