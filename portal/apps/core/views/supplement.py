# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.utils.timezone import now

from decorators import render_response
from core.models import Supplement


to_response = render_response('core/templates/supplement/')


@never_cache
@to_response
def supplement_list(request):
    supplements = Supplement.objects.filter(public=True).order_by('-date_published')
    paginator, page = Paginator(supplements, 20), request.GET.get('pagina')
    try:
        supplements = paginator.page(page)
    except PageNotAnInteger:
        supplements = paginator.page(1)
    except (EmptyPage, InvalidPage):
        supplements = paginator.page(paginator.num_pages)
    return 'list.html', {'supplements': supplements}


@never_cache
@to_response
def supplement_download(request, supplement_slug, year, month, day):
    supplement = get_object_or_404(
        Supplement,
        slug=supplement_slug,
        date_published__year=year,
        date_published__month=month,
        date_published__day=day,
    )
    return supplement.download(request)


@to_response
def supplement_email(request):
    return (
        'supplement_email.html',
        {'supplement': get_object_or_404(Supplement, date_published=now().date(), public=True)},
    )
