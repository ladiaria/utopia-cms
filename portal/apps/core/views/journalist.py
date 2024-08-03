# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from core.models import Journalist


@never_cache
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
    return render(
        request,
        getattr(settings, "CORE_JOURNALIST_DETAIL_TEMPLATE", 'core/templates/journalist.html'),
        {'journalist': journalist, 'articles': articles},
    )
