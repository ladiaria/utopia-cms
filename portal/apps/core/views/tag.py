# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import Http404
from django.template.defaultfilters import slugify
from django.views.decorators.cache import never_cache
from django.shortcuts import render

from tagging.models import Tag, TaggedItem

from core.models import Article


@never_cache
def tag_detail(request, tag_slug):
    tags = []
    for tag in Tag.objects.iterator():
        if slugify(tag.name) == tag_slug:
            tags.append(tag)
    if not tags:
        raise Http404
    paginator = Paginator(TaggedItem.objects.get_by_model(Article, tags).filter(is_published=True), 10)
    try:
        page = int(request.GET.get('pagina', '1'))
    except ValueError:
        page = 1
    try:
        articles = paginator.page(page)
    except (EmptyPage, InvalidPage):
        articles = paginator.page(paginator.num_pages)
    # support to render a custom template if only one tag and the tag is a TagGroup member (first group found taken)
    template, gt_dir = 'core/templates/article/list.html', getattr(settings, 'GROUPEDTAGS_TEMPLATE_DIR', None)
    if gt_dir and len(tags) == 1:
        tg = tags[0].taggroup_set.first()
        if tg and tg.slug in getattr(settings, 'GROUPEDTAGS_CUSTOM_TEMPLATES', ()):
            # use the custom template
            template = '%s/%s.html' % (gt_dir, tg.slug)
    return render(request, template, {'tags': tags, 'articles': articles})
