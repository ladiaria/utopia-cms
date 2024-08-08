# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache

from decorators import render_response

from core.models import Journalist


to_response = render_response('core/templates/')


@never_cache
@to_response
def journalist_detail(request, journalist_job, journalist_slug):
    journalist_job = journalist_job[:2].upper()
    other_job = 'CO' if journalist_job == 'PE' else 'PE'
    try:
        journalist = Journalist.objects.get(slug=journalist_slug, job=journalist_job)
    except Journalist.DoesNotExist:
        # Maybe it has the other job, if so, redirect:
        journalist = get_object_or_404(Journalist, slug=journalist_slug, job=other_job)
        return HttpResponsePermanentRedirect(journalist.get_absolute_url())

    articles = journalist.articles_core.filter(is_published=True)
    paginator, page = Paginator(articles, 20), request.GET.get('pagina')
    try:
        articles = paginator.page(page)
    except PageNotAnInteger:
        articles = paginator.page(1)
    except (EmptyPage, InvalidPage):
        articles = paginator.page(paginator.num_pages)
    return 'journalist.html', {'journalist': journalist, 'articles': articles}
