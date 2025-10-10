# -*- coding: utf-8 -*-
from datetime import timedelta

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.feedgenerator import Rss201rev2Feed, rfc2822_date

from libs.utils import get_site_name
from core.models import Article, get_current_edition, get_current_feeds, Journalist, Section, Supplement, Edition
from core.templatetags.ldml import ldmarkup, cleanhtml

site_name = get_site_name()


def _cdata_element(handler, tag, text):
    """Escribe una etiqueta completa con CDATA, segura para Django 4.2."""
    if text is None:
        return
    safe = str(text).replace("]]>", "]]]]><![CDATA[>")
    handler._write(f"<{tag}><![CDATA[{safe}]]></{tag}>")


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

    def add_root_elements(self, handler):
        super().add_root_elements(handler)

    def add_item_elements(self, handler, item):
        guid = item.get('unique_id')
        if guid:
            is_perm = item.get('unique_id_is_permalink')
            attrs = {}
            if is_perm is not None:
                attrs['isPermaLink'] = 'true' if is_perm else 'false'
            handler.addQuickElement('guid', guid, attrs)

        pubdate = item.get('pubdate')
        if pubdate:
            pubdate = timezone.localtime(pubdate)
            handler.addQuickElement('pubDate', rfc2822_date(pubdate))

        title = item.get('title')
        if title:
            _cdata_element(handler, 'title', title)

        description = item.get('description')
        if description:
            _cdata_element(handler, 'description', description)

        author = item.get('author_name')
        if author:
            _cdata_element(handler, 'dc:creator', author)

        image_url = item.get('image_url')
        image_title = item.get('image_title')
        if image_url:
            handler._write("<image:image>")
            handler.addQuickElement('image:loc', image_url)
            if image_title:
                _cdata_element(handler, 'image:title', image_title)
            handler._write("</image:image>")

        categories = item.get('categories_cdata') or []
        for cat in categories:
            if cat:
                _cdata_element(handler, 'category', cat)

        link = item.get('link')
        if link:
            handler.addQuickElement('link', link)


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

    def item_author_name(self, item):
        authors = item.get_authors()
        return authors[0] if authors else ""

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

        if image_url and image_url.startswith("/"):
            image_url = f"{settings.URL_SCHEME}://{settings.SITE_DOMAIN}{image_url}"

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


class LatestArticles72hs(LatestArticles):
    title = f"{site_name}"
    description = f"Artículos publicados en las últimas 72 horas en {site_name}."

    def feed_url(self):
        return f"{settings.URL_SCHEME}://{settings.SITE_DOMAIN}/feeds/articulos_rss_72hs.xml"

    def items(self):
        cutoff = timezone.localtime(timezone.now()) - timedelta(hours=72)
        return Article.published.filter(date_published__gte=cutoff).order_by('-date_published')


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
