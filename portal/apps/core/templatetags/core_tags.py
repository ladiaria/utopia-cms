# -*- coding: utf-8 -*-
import os
import re
import random
from datetime import date, timedelta

from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Library, Node, RequestContext, TemplateSyntaxError, Variable, loader
from django.template.defaultfilters import stringfilter
from django.utils.text import Truncator

from core.models import Article, Supplement, Category, Section
from core.forms import SendByEmailForm
from core.templatetags.ldml import ldmarkup, cleanhtml


register = Library()


@register.simple_tag(takes_context=True)
def render_related(context, article):

    article, section = context.get('article'), context.get('section')
    if not section:
        return u''

    category, publication = section.category, context.get('publication')

    if publication and section.slug not in getattr(settings, 'CORE_SECTIONS_EXCLUDE_RELATED', ()) and \
            publication.slug not in getattr(settings, 'CORE_PUBLICATIONS_EXCLUDE_RELATED', ()):
        return loader.render_to_string('core/templates/article/related.html', {
            'articles': section.latest4relatedbypublication(publication.id, article.id), 'is_detail': False,
            'section': publication.name})

    elif category and category.slug in getattr(settings, 'CORE_CATEGORY_REALTED_USE_CATEGORY', ()):
        return loader.render_to_string('core/templates/article/related.html', {
            'articles': section.latest4relatedbycategory(category.id, article.id), 'is_detail': False,
            'section': category.name})

    elif 'elecciones' in article.get_categories_slugs() and section.slug not in (
            'apuntes-de-campana', 'entrevistas-elecciones-2019', 'datos-elecciones-2019'):
        try:
            category = Category.objects.get(slug='elecciones')
            return loader.render_to_string('core/templates/article/related.html', {
                'articles': section.latest4relatedbycategory(category.id, article.id), 'is_detail': False,
                'section': category.name})
        except Category.DoesNotExist:
            pass

    return loader.render_to_string('core/templates/article/related.html', {
        'articles': section.latest4related(article.id), 'is_detail': False, 'section': section.name})


# Media select
class MediaSelectNode(Node):
    def __init__(self, name):
        self.name = name

    def render(self, context):
        medias = (
            {'id': 'I', 'name': 'Image'},
            {'id': 'A', 'name': 'Audio'},
            {'id': 'V', 'name': 'Video'},
        )
        select_html = loader.render_to_string(
            'core/templates/media_select.html',
            {'medias': medias, 'select_name': self.name})
        return select_html


@register.tag
def media_select(parser, token):
    bits = token.contents.split()[2:]
    # No quiero las posiciones 0 y 1 porque son el nombre del tag y la keyword
    # "with" respectivamente.
    kwargs = {}
    for param in bits:
        key, val = [str(p) for p in param.split('=')]
        kwargs[key] = val.replace('"', '')
    return MediaSelectNode(**kwargs)


@register.simple_tag(takes_context=True)
def render_article_card(context, article, media, card_size, card_type=None, img_load_lazy=True):
    if not card_size:
        card_size = article.header_display

    verbose_date = None

    if not card_type:
        card_type = article.type

    card_display = "vertical"
    if article.photo and article.photo.extended.is_portrait:
        card_display = "horizontal"
    if article.photo and article.photo.extended.is_landscape:
        card_display = "vertical"

    verbose_date = None
    if article.date_published.date() == date.today():
        verbose_date = "Hoy"
    elif article.date_published.date() == date.today() - timedelta(1):
        verbose_date = "Ayer"

    # WARN: template value assigned here may change in next if block. TODO: fix this anti-pattern.
    if card_size == "FW":
        template = "card_full.html"
    elif card_size == "FD":
        template = "card_full_detailed.html"
    elif card_size == "FF":
        template = "card_big_new.html"
        card_display = "horizontal"
    elif card_size == "BG":
        template = "card_big.html"
    elif card_size == "MD":
        template = "card_medium.html"
    elif card_size == "SM":
        template = "card_small.html"
        media = "none"
    elif card_size == "OC":
        template = "card_big.html"
    else:
        template = "card_medium.html"

    # WARN: again, template may change in next if block.
    if card_type == 'OP':
        card_display = "horizontal"
        template = "card_opinion.html"
    elif card_type == 'SU':
        template = "card_summary.html"

    if card_size == "FN":
        template = "article_card_new.html"

    context.update(
        {
            'article': article,
            'media': media,
            'card_size': card_size,
            'card_display': card_display,
            'card_type': card_type,
            'verbose_date': verbose_date,
            'img_load_lazy': img_load_lazy,
        }
    )
    return loader.render_to_string('core/templates/article/' + template, context.flatten())


# Render article media list con foto a la izquierda para mostrar en sidebar
class RenderArticleMediaNode(Node):
    def __init__(self, article=None, media=None):
        self.article = Variable(article)
        self.media = Variable(media)

    def render(self, context):
        article = self.article.resolve(context)
        if not article:
            return ''
        media = self.media.resolve(context)
        context.update({'articles': [article], 'media': media, 'separador': True})
        article_html = loader.render_to_string(
            'core/templates/article/media-list.html',
            context=context.flatten(), request=context.request)
        return article_html


@register.tag
def render_article_media(parser, token):
    bits = token.contents.split()[2:]
    kwargs = {}
    for param in bits:
        key, val = [str(p) for p in param.split('=')]
        kwargs[key] = val.replace('"', '')
    return RenderArticleMediaNode(**kwargs)


class ArticlesByTypeNode(Node):
    def __init__(self, type, keyword, limit=0):
        if type.startswith('"'):
            self.type = type.strip('"')
        else:
            self.type = Variable(type)
        self.keyword = keyword
        try:
            self.limit = int(limit)
        except ValueError:
            self.limit = Variable(limit)

    def render(self, context):
        from string import upper
        if isinstance(self.type, Variable):
            type = getattr(Article, upper(self.type.resolve(context)))
        else:
            type = getattr(Article, upper(self.type))
        articles = Article.objects.filter(is_published=True, type=type)
        if self.limit:
            articles = articles[:self.limit]
        context.update({self.keyword: articles})
        return ''


@register.tag
def get_articles_by_type(parser, token):
    """Usage:
    {% get_articles_by_type 10 "ombudsman" as article_list %}
    or
    {% get_articles_by_type "ombudsman" as article_list %}
    """

    bits = token.contents.split()
    limit = None
    if len(bits) == 4:
        type = bits[1]
        keyword = bits[3]
    elif len(bits) == 5:
        limit = bits[1]
        type = bits[2]
        keyword = bits[4]
    else:
        raise TemplateSyntaxError('Invalid syntax for %s' % bits[0])
    return ArticlesByTypeNode(type=type, keyword=keyword, limit=limit)


class DefensoriaNode(Node):
    def render(self, context):
        html = ''
        defensoria_template = 'core/templates/article/lead.html'
        articles = Article.objects.filter(
            is_published=True, type=Article.OMBUDSMAN).order_by(
                '-date_published')
        for article in articles:
            params = {'article': article, 'ignore_toolbar': True}
            html += loader.render_to_string(
                defensoria_template, params,
                context=RequestContext(context['request']))
        return html


@register.tag
def defensoria(parser, token):
    return DefensoriaNode()


@register.simple_tag(takes_context=True)
def render_toolbar_for(context, toolbar_object):
    """ Usage example: {% render_toolbar_for article %} """
    user = context.get('user')
    if user and user.is_staff and isinstance(toolbar_object, Article):
        toolbar_template = 'core/templates/article/toolbar.html'
        params = {'article': toolbar_object, 'is_detail': False}
        if context.get('is_cover'):
            edition = context.get('edition')
            if edition:
                params.update(
                    {
                        'featured_order': ', '.join(
                            str(tp) for tp in toolbar_object.articlerel_set.filter(
                                edition=edition, home_top=True
                            ).values_list('top_position', flat=True)
                        ),
                    }
                )
        context.update(params)
        return loader.render_to_string(toolbar_template, context.flatten())
    else:
        return u''


@register.simple_tag
def render_supplements():
    supplements = Supplement.objects.all()[:2]
    return loader.render_to_string(
        'core/templates/supplement_list.html', {'supplements': supplements})


@register.simple_tag
def render_hierarchy(article):
    """
    Returns HTML to print links with the article hierarchy using its main category (or publication if the category is
    None and publication is included in the custom setting) and its main section.
    """
    section = article.section
    if section:
        if section.category:
            parent = (reverse('home', kwargs={'domain_slug': section.category.slug}), section.category)
        else:
            parent = None if (
                not article.main_section or article.main_section.edition.publication.slug in
                getattr(settings, 'CORE_HIERARCHY_USE_PUBLICATION', ())
            ) else (
                reverse('home', kwargs={'domain_slug': article.main_section.edition.publication.slug}),
                article.main_section.edition.publication,
            )
        child = u'<a href="%s">%s</a>' % (section.get_absolute_url(), section)
        return u' › '.join([u'<a href="%s">%s</a>' % parent, child]) if parent else child
    else:
        return u''


@register.simple_tag(takes_context=True)
def publication_section(context, article, pub=None):
    """
    Returns the anchor tag with the atricle.publication_section using the publication given by parameter or publication
    context variable as publication argument (or default_pub if None).
    """
    section = article.publication_section(pub or context.get('publication') or context.get('default_pub'))
    return (u'<a href="%s">%s</a>' % (section.get_absolute_url(), section)) if section else u''


@register.simple_tag(takes_context=True)
def category_nl_subscribe_box(context):
    """ renders the subscribe box for the article category, if proper conditions are met """
    # TODO: can be improved and even removed making some modifications in caller templates
    subscriber = getattr(context.get('user'), 'subscriber', None)
    subscriber_nls = subscriber.get_newsletters_slugs() if subscriber else []
    category = context.get('category')

    if category and category.has_newsletter:
        # article has category with nl
        if category.slug not in subscriber_nls:
            return loader.render_to_string('core/templates/article/subscribe_box_category.html', context.flatten())

    return u''


# Inclusion tags
@register.inclusion_tag("article/_send_by_email_form.html")
def send_by_email_form(user):
    return {"form": SendByEmailForm(), "user": user}


# Filters
def name_wrap(name):
    return loader.render_to_string(
        'core/templates/byline.html', {'name': name})


@register.filter
@stringfilter
def initials(value, args=False):
    from django.template.defaultfilters import safe
    ret = ''
    names = value.split(', ')
    if not args:
        for name in names:
            ret += name_wrap(name)
    else:
        for name in names:
            full_name = name.split(' ')
            first = full_name[0][0].upper()
            second = full_name[1][0].upper()
            ret += name_wrap(first + second)
    return safe(ret)


@register.filter(name='anios')
def anios(last):
    return range(2009, last)


@register.filter
def remove_markup(value):
    if value:
        value = re.sub(r"__recuadro__.", "", value)
        value = value.replace("__recuadro__", "")
        value = re.sub(r"__imagen__.", "", value)
        value = value.replace("__imagen__", "")
        # quitamos cualquier link que haya quedado
        value = re.sub(r"\(http(.*)\)", "", value)
        value = cleanhtml(ldmarkup(value))
        value = value.replace("[", "")
        value = value.replace("]", "")
    else:
        value = u''
    return value


@register.filter
def truncatehtml(string, length):
    truncator = Truncator(string)
    return truncator.words(length, html=True)


truncatehtml.is_safe = True


# randomgen is taken from https://github.com/bkeating/django-templatetag-randomgen and fixed (*) here
@register.tag(name="randomgen")
def randomgen(parser, token):
    items = []
    bits = token.split_contents()
    for item in bits:
        items.append(item)
    return RandomgenNode(items[1:])


class RandomgenNode(Node):
    def __init__(self, items):
        self.items = []
        for item in items:
            self.items.append(item)

    def render(self, context):
        # (*) Note: we fixed index error in arg1 and arg2, but they can still raise errors if not passed correctly
        arg1 = self.items[0] if self.items else None
        arg2 = self.items[1] if len(self.items) > 1 else None
        if "hash" in self.items:
            result = os.urandom(16).encode('hex')
        elif "float" in self.items:
            result = random.uniform(int(arg1), int(arg2))
        elif not self.items:
            result = random.random()
        else:
            result = random.randint(int(arg1), int(arg2))
        return result
