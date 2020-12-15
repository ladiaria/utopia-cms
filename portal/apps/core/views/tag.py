# -*- coding: utf-8 -*-
from decorators import render_response
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import Http404
from django.template.defaultfilters import slugify
from django.views.decorators.cache import never_cache

from tagging.models import Tag, TaggedItem

from core.models import Article

to_response = render_response('core/templates/article/')


@never_cache
@to_response
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
    return 'list.html', {'tags': tags, 'articles': articles}
