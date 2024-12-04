# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.http import HttpResponsePermanentRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from core.models import Journalist


@never_cache
def journalist_detail(request, journalist_job, journalist_slug, template_name=None):
    journalist_job, get_kwargs = journalist_job[:2].upper(), {"slug": journalist_slug}
    use_job = settings.CORE_JOURNALIST_GET_ABSOLUTE_URL_USE_JOB
    if use_job:
        get_kwargs["job"] = journalist_job
    try:
        journalist = Journalist.objects.get(**get_kwargs)
        if not use_job and journalist_job in ("PE", "CO"):
            if journalist.job != journalist_job:
                raise Http404
            return HttpResponsePermanentRedirect(journalist.get_absolute_url())
    except Journalist.DoesNotExist:
        if use_job:
            # Maybe it has the other job, if so, redirect
            get_kwargs["job"] = 'CO' if journalist_job == 'PE' else 'PE'
            journalist = get_object_or_404(Journalist, **get_kwargs)
            return HttpResponsePermanentRedirect(journalist.get_absolute_url())
        raise

    articles = journalist.articles_core.filter(is_published=True)
    paginator, page = Paginator(articles, 20), request.GET.get('pagina')
    try:
        articles = paginator.page(page)
    except PageNotAnInteger:
        articles = paginator.page(1)
    except (EmptyPage, InvalidPage):
        articles = paginator.page(paginator.num_pages)
    return render(
        request, template_name or 'core/templates/journalist.html', {'journalist': journalist, 'articles': articles}
    )
