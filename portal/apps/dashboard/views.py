# coding=utf-8
from os.path import join
import csv
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from django.conf import settings

from decorators import render_response

from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import permission_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from audiologue.models import Audio

from dashboard.models import AudioStatistics


to_response = render_response('dashboard/templates/')


@never_cache
@permission_required('thedaily.change_subscriber')
@to_response
def index(request):
    is_admin, is_seller, is_financial = request.user.is_superuser, False, False
    if not is_admin:
        user_groups = request.user.groups.all()
        is_seller = get_object_or_404(Group, name=getattr(settings, 'DASHBOARD_SELLER_GROUP', None)) in user_groups
        is_financial = get_object_or_404(
            Group, name=getattr(settings, 'DASHBOARD_FINANCIAL_GROUP', None)) in user_groups
    return 'index.html', {
        'activity_rows': is_admin or is_seller, 'is_financial': is_admin or is_financial,
        'financial_extra_items_template': getattr(settings, 'DASHBOARD_FINANCIAL_EXTRA_ITEMS_TEMPLATE', None)}


@never_cache
@permission_required('thedaily.change_subscriber')
@to_response
def load_table(request, table_id):

    month = request.GET.get('month')
    year = request.GET.get('year')
    today = date.today()

    if table_id in ('activity', 'activity_only_digital'):
        # Alow only admins or member of seller group
        if not (request.user.is_superuser or get_object_or_404(
                Group, name=getattr(settings, 'DASHBOARD_SELLER_GROUP', None)) in request.user.groups.all()):
            return HttpResponseForbidden()

    if month and year and table_id not in ('activity', 'activity_only_digital'):
        date_start = date(int(year), int(month), 1)
        date_end = date_start + relativedelta(months=1)
        last_month = today - relativedelta(months=1)
        if int(month) == last_month.month and int(year) == last_month.year:
            filename = '%s.csv' % table_id
        else:
            filename = '%s%s_%s.csv' % (year, month, table_id)
    else:
        date_end = date(today.year, today.month, 1)
        date_start = date_end - relativedelta(months=1)
        filename = '%s.csv' % table_id
    try:
        rows = csv.reader(open(join(settings.DASHBOARD_REPORTS_PATH, filename)))
        # hardcoded last year filter only for subscribers
        # TODO: implement the year selector
        if table_id == 'subscribers':
            rows = [row for row in rows if row[1].startswith('2019')]
    except Exception:
        rows = None
    else:
        # TODO: show warning if we know the data for the selected table/date was not generated correctly
        pass

    return 'table.html', {
        'rows': rows, 'table_id': table_id, 'month': month, 'year': year, 'date_start': date_start,
        'date_end': date_end}


@never_cache
@permission_required('thedaily.change_subscriber')
def export_csv(request, table_id):
    resp = HttpResponse(
        content=open(join(settings.DASHBOARD_REPORTS_PATH, '%s.csv' % table_id)).read(), content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename=%s.csv' % table_id
    return resp


@require_http_methods(["POST"])
def audio_statistics_api(request):
    subscriber_id = request.POST.get('subscriber_id')
    audio_id = request.POST.get('audio_id')
    percentage = request.POST.get('percentage')
    percentage = int(percentage)

    if AudioStatistics.objects.filter(
            subscriber_id=subscriber_id, audio_id=audio_id, percentage=percentage).exists():
        return HttpResponse()
    else:
        try:
            audio_statistics, created = AudioStatistics.objects.get_or_create(
                subscriber_id=subscriber_id, audio_id=audio_id)
            if audio_statistics.percentage < percentage:
                audio_statistics.percentage = percentage
                audio_statistics.save()
                return HttpResponse()
            return HttpResponse()
        except ValidationError:
            raise HttpResponseBadRequest("Unique object already exists")


@never_cache
@permission_required('thedaily.change_subscriber')
@to_response
def audio_statistics_dashboard(request):
    audios = Audio.objects.all().order_by('-id')
    for audio in audios:
        articles = audio.articles_core.all()
        if articles:
            audio.article = articles[0].headline
            audio.area = articles[0].section
            audio.date = articles[0].date_published
        else:
            pass
        # Not sure why this doesn't work. Raises UnicodeDecodeError
        # audio_info = mutagen.File(audio.file).info
        # audio.duration = timedelta(seconds=int(audio_info.length))
        audio.clicks = audio.audiostatistics_set.filter().count()
        audio.percentage0 = audio.audiostatistics_set.filter(percentage=0).count()
        audio.percentage25 = audio.audiostatistics_set.filter(percentage=25).count()
        audio.percentage50 = audio.audiostatistics_set.filter(percentage=50).count()
        audio.percentage75 = audio.audiostatistics_set.filter(percentage=75).count()

    return 'audio_statistics.html', {'audios': audios}
