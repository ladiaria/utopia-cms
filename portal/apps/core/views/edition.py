# -*- coding: utf-8 -*-
from datetime import date, timedelta

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe

from decorators import render_response
from libs.tokens.email_confirmation import download_token_generator
from core.models import Edition, Supplement, get_current_edition
from homev3.views import index
from core.views.edition_calendar import EditionCalendar

to_response = render_response('core/templates/edition/')


@never_cache
@to_response
def edition_list(request):
    editions = Edition.objects.all().order_by('-date_published')
    paginator = Paginator(editions, 21)
    try:
        page = int(request.GET.get('pagina', '1'))
    except ValueError:
        page = 1
    try:
        editions = paginator.page(page)
    except (EmptyPage, InvalidPage):
        editions = paginator.page(paginator.num_pages)
    return 'list.html', {'editions': editions}


@to_response
def edition_list_ajax(request, year, month):
    editions = Edition.objects.all().order_by('-date_published').filter(
        date_published__year=year, date_published__month=month)
    cal = EditionCalendar(editions, settings.FIRST_DAY_OF_WEEK, settings.LOCALE_NAME).formatmonth(year, month)
    return 'list_ajax.html', {'calendar': mark_safe(cal)}


@never_cache
def edition_detail(request, year, month, day, publication_slug=None):
    return index(request, year, month, day, publication_slug)


@never_cache
def is_valid_download_link(request):
    try:
        uid, ts, token = request.GET.copy().get('token', '').split('-')
    except Exception:
        raise Http404
    user = get_object_or_404(User, id=uid)
    return download_token_generator.check_token(
        user=user, token='%s-%s' % (ts, token), timeout_days=1)


@never_cache
def get_download_validation_url(edition, user):
    url = reverse('edition_download', args=(), kwargs={
        'year': edition.date_published.year,
        'month': edition.date_published.month,
        'day': edition.date_published.day})
    return '%s?token=%i-%s' % (
        url, user.id, download_token_generator.make_token(user))


@never_cache
@to_response
@login_required
def edition_download(request, publication_slug, year, month, day, filename):
    try:
        date_published = date(int(year), int(month), int(day))
    except ValueError:
        raise Http404
    edition = get_object_or_404(Edition, publication__slug=publication_slug, date_published=date_published)
    downloadable_editions = getattr(settings, 'CORE_PUBLICATIONS_EDITION_DOWNLOAD', ())
    if request.user.is_staff or (
            publication_slug == settings.DEFAULT_PUB and request.user.subscriber.is_subscriber() and
            request.user.subscriber.pdf
        ) or (
            publication_slug in downloadable_editions and request.user.subscriber.is_subscriber(publication_slug) and
            getattr(request.user.subscriber, publication_slug + '_pdf', False)):
        if request.user.is_superuser or (date.today() - timedelta(70) < date_published):
            return (
                edition if edition.pdf.name.endswith(filename) else
                get_object_or_404(Supplement, edition=edition, pdf__endswith=filename)).download(request)

    return HttpResponseForbidden()


def rawpic_cover(request):
    edition = get_current_edition()
    if not edition:
        response = HttpResponse(
            "No hay foto disponible!", mimetype="text/plain")
    else:
        rawpic = open(edition.cover.path)
        response = HttpResponse(rawpic.read(), mimetype="image/jpeg")
    return response
