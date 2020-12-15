# -*- coding: utf-8 -*-
from datetime import date
from core.models import Supplement

from decorators import render_response

from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache

to_response = render_response('core/templates/supplement/')


@never_cache
@to_response
def supplement_list(request):
    supplements = Supplement.objects.filter(public=True).order_by(
        '-date_published')
    paginator = Paginator(supplements, 20)
    try:
        page = int(request.GET.get('pagina', '1'))
    except ValueError:
        page = 1
    try:
        supplements = paginator.page(page)
    except (EmptyPage, InvalidPage):
        supplements = paginator.page(paginator.num_pages)
    return 'list.html', {'supplements': supplements}


@never_cache
@to_response
def supplement_download(request, supplement_slug, year, month, day):
    supplement = get_object_or_404(
        Supplement, slug=supplement_slug, date_published__year=year,
        date_published__month=month, date_published__day=day)
    return supplement.download(request)


@to_response
def supplement_email(request):
    from django.shortcuts import get_object_or_404
    return 'supplement_email.html', {'supplement': get_object_or_404(
        Supplement, date_published=date.today(), public=True)}
