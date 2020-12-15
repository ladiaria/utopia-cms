# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.core.exceptions import ObjectDoesNotExist

from core.models import Article, get_current_edition, get_current_feeds, Journalist, Section, Supplement, Edition

from core.templatetags.ldml import ldmarkup, cleanhtml


class LatestArticles(Feed):
    title = u'la diaria'
    link = '/'
    description = u'Artículos de la publicación periodística la diaria.'

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
        return datetime(
            item.date_published.year, item.date_published.month,
            item.date_published.day)

    def item_author_name(self, item):
        if item.get_authors():
            return item.get_authors()[0]
        else:
            return ""

    def item_categories(self, item):
        return [item.get_sections()]


class LatestArticlesByCategory(Feed):

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        return Section.objects.get(slug=bits[0])

    def title(self, obj):
        return u'la diaria - %s' % (obj.name)

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return u'Artículos de la sección "%s" de la diaria.' % (obj.name)

    def items(self, obj):
        edition = get_current_edition()
        return obj.articles.filter(
            is_published=True,
            edition__id__lte=edition.id).order_by('-date_published')[:10]


class LatestArticlesByType(Feed):
    link = '/'

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        VALID_TYPES = (
            # (URL, CODE, VERBOSE),
            ('variedad', Article.FEATURE, 'Variedad'),
            ('noticia', Article.NEWS, 'Noticia'),
            ('ombudsman', Article.OMBUDSMAN, 'Defensor del lector'),
            ('opinion', Article.OP_ED, 'Opinión'),
            ('foto-reportaje', Article.PHOTO_ARTICLE, 'Foto-reportajes'),
        )
        for vtype in VALID_TYPES:
            if vtype[0] == bits[0]:
                self.type = vtype[1]
                self.type_verbose = vtype[2]
                return None
        raise ObjectDoesNotExist

    def title(self, obj):
        return u'la diaria - %s' % (self.type_verbose)

    def description(self, obj):
        return u'Artículos de tipo "%s" de la diaria ' % (self.type_verbose)

    def items(self, obj):
        edition = get_current_edition()
        return Article.objects.filter(
            type=self.type, is_published=True,
            edition__id__lte=edition.id).order_by(
                '-date_published')[:10]

    def item_link(self, obj):
        return obj.get_absolute_url()


class LatestEditions(Feed):
    title = u'la diaria - Ediciones'
    description = u'Ediciones de la publicación periodística la diaria.'

    def link(self, obj):
        return obj.get_absolute_url()

    def items(self):
        print('items')
        edition = get_current_edition()
        return Edition.objects.filter(id__lte=edition.id)[:10]


class LatestSupplements(Feed):
    title = u'la diaria - Suplementos'
    description = \
        u'Suplementos de la publicación periodística la diaria.'

    def link(self, obj):
        return obj.get_absolute_url()

    def items(self):
        edition = get_current_edition()
        query = Supplement.objects.filter(edition__id__lte=edition.id)[:10]
        result = query.exclude(public=False)
        return result


# FIXME: AttributeError: 'NoneType' object has no attribute 'startswith'
class ArticlesByJournalist(Feed):

    def title(self, obj):
        return u'la diaria - %s' % obj.name

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        if not Journalist.objects.filter(name=bits[0]).count():
            raise ObjectDoesNotExist
        return Journalist.objects.get(name=bits[0])

    def description(self, obj):
        return u'Artículos escritos por %s' % self.journalist.name

    def items(self, obj):
        edition = get_current_edition()
        return Article.objects.filter(
            journalist=obj, is_published=True,
            edition__id__lte=edition.id).order_by(
                '-date_published')[:10]

    def item_link(self, obj):
        return obj.get_absolute_url()

    def item_pubdate(self, obj):
        return obj.date_published


def articles_feed_wrapper(*args, **kwargs):
    if len(args[1].META.get('PATH_INFO').strip('/').split('/')) == 2:
        return LatestArticles(*args, **kwargs)
    else:
        return LatestArticlesByType(*args, **kwargs)
