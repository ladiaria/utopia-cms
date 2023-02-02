# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.http import Http404
from django.template.defaultfilters import slugify
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect

from tagging.models import Tag, TaggedItem

from core.models import Article


@never_cache
def tag_detail(request, tag_slug):
    """
    Get tag detail from given tag slug.
    If given tag slug it's not slugified then redirect to the slugified urls version.
    Otherwise, try to get and return tags
    params: tag_slug: string
    """
    tag_slugified = slugify(tag_slug)
    if tag_slugified != tag_slug:
        return redirect('tag_detail', tag_slug=tag_slugified)
    tags = [tag for tag in Tag.objects.iterator() if slugify(tag.name) == tag_slug]

    if not tags:
        raise Http404
    paginator = Paginator(TaggedItem.objects.get_by_model(Article, tags).filter(is_published=True), 10)
    page = request.GET.get('pagina')
    try:
        articles = paginator.page(page)
    except PageNotAnInteger:
        articles = paginator.page(1)
    except (EmptyPage, InvalidPage):
        articles = paginator.page(paginator.num_pages)
    # support to render a custom template if only one tag and the tag is a TagGroup member (first group found taken)
    template, gt_dir = 'core/templates/article/list.html', getattr(settings, 'GROUPEDTAGS_TEMPLATE_DIR', None)
    if gt_dir and len(tags) == 1:
        tg = tags[0].taggroup_set.first()
        if tg and tg.slug in getattr(settings, 'GROUPEDTAGS_CUSTOM_TEMPLATES', ()):
            # use the custom template
            template = '%s/%s.html' % (gt_dir, tg.slug)
    return render(
        request,
        template,
        {
            'tags': tags,
            'articles': articles,
            "title_append_country": getattr(settings, "CORE_TAG_DETAIL_TITLE_APPEND_COUNTRY", True),
        },
    )
