# -*- coding: utf-8 -*-
# utopia-cms Markup Language

import re

from markdown2 import markdown

from django.conf import settings
from django.template import Library
from django.template.loader import render_to_string
from django.template.defaultfilters import stringfilter
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags


register = Library()

TITLES_RE = r'^\s*S>\s*(.*[^\s])\s*$'
EXTENSION_KW = getattr(settings, 'CORE_ARTICLE_DETAIL_EXTENSION_KW', '__recuadro__')
EXTENSION_RE = r'%s\s*(\d*)' % EXTENSION_KW

IMAGE_KW = getattr(settings, 'CORE_ARTICLE_DETAIL_IMAGE_KW', '__imagen__')
IMAGE_RE = r'%s\s*(\d*)' % IMAGE_KW
MD_EXTRAS = ['abbr', "footnotes", "tables", "headerid", 'attr_list', 'extra', "strike"]


def normalize(value):
    nre = re.compile(r'\r\n|\r|\n')
    return nre.sub('\n', force_str(value))


def to_p(value):
    value = value.strip()
    if not value.startswith('<') and not value == '':
        return '<p>%s</p>' % value
    return value


def get_extension(match, aid):
    from core.models import ArticleExtension

    if match.groups()[0] == '':
        count = 0
    else:
        count = int(match.groups()[0]) - 1
    extensions = ArticleExtension.objects.filter(article__id=aid)
    if extensions.count() > count and count >= 0:
        extension = extensions[count]
    else:
        return ''
    return render_to_string('core/templates/article/extension.html', {'extension': extension})


def get_image(match, aid, amp=False):
    from core.models import Article

    if match.groups()[0] == '':
        count = 0
    else:
        count = int(match.groups()[0]) - 1

    try:
        article = Article.objects.prefetch_related('body_image__image').get(id=aid)
        images = article.body_image.all()
        if images.count() > count and count >= 0:
            article_body_image = images[count]
            # ensure the image file exists
            try:
                bool(article_body_image.image.image.file)
            except IOError:
                return ''
            else:
                return render_to_string(
                    'core/templates/%sarticle/image.html' % ('amp/' if amp else ''),
                    {'article': article, 'image': article_body_image.image, 'display': article_body_image.display},
                )
        else:
            return ''
    except Article.DoesNotExist:
        return ''


@register.simple_tag
def photo_byline(article, allowed=True):
    # if allowed by setting and not disallowed by the allow arg given, it returns the article's "photo_autor" entry if
    # article arg is dict (useful in "offline" rendering), otherwise (if it is an Article object) returns the method.
    if settings.CORE_ARTICLE_ENABLE_PHOTO_BYLINE and allowed:
        return (dict.get if isinstance(article, dict) else getattr)(article, "photo_author", "")
    else:
        return ""


@register.filter
@stringfilter
def ldmarkup(value, args='', amp=False):
    """ Usage: {% article.body|ldmarkup:article.id %} """
    value = normalize(value)
    value = strip_tags(value)
    reg = re.compile(TITLES_RE, re.UNICODE + re.MULTILINE)
    value = reg.sub(r'\n\n\1\n----', value)
    if args:
        # TODO: Si hay un recuadro al final le aplica full width a todos los recuadros del artículo.
        #       translate2english this comment asap or make it at all
        reg = re.compile(EXTENSION_RE, re.UNICODE + re.MULTILINE)
        value = reg.sub(lambda x: get_extension(x, args), value)
        reg = re.compile(IMAGE_RE, re.UNICODE + re.MULTILINE)
        value = reg.sub(lambda x: get_image(x, args, amp), value)
    return mark_safe(force_str(markdown(value, extras=MD_EXTRAS).strip()))


@register.filter
@stringfilter
def ldmarkup_extension(value, args='', amp=False):
    """ Usage: {% article.body|ldmarkup_extension %} """
    reg = re.compile(TITLES_RE, re.UNICODE + re.MULTILINE)
    value = reg.sub(r'\n\n\1\n----', value)
    value = markdown(value, extras=MD_EXTRAS).strip()
    return mark_safe(force_str(value))


@register.filter
@stringfilter
def amp_ldmarkup(value, args=''):
    """
    Wrapper of ldmarkup for amp
    Usage: {% article.body|amp_ldmarkup:article.id %}
    """
    return ldmarkup(value, args, True)


@register.filter
def remove_markup(value):
    if value:
        value = re.sub(fr"{EXTENSION_KW}.", "", value)
        value = value.replace(EXTENSION_KW, "")
        value = re.sub(fr"{IMAGE_KW}.", "", value)
        value = value.replace(IMAGE_KW, "")
        # quitamos cualquier link que haya quedado
        value = re.sub(r"\(http(.*)\)", "", value)
        value = cleanhtml(ldmarkup(value))
        value = value.replace("[", "")
        value = value.replace("]", "")
    else:
        value = ''
    return value


def cleanhtml(html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', html)
