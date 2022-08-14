# coding=utf-8
from __future__ import unicode_literals
from os.path import join
from csv import reader, writer
from datetime import date
from dateutil.relativedelta import relativedelta

from django.conf import settings

from decorators import render_response

from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import permission_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from core.models import Article
from .models import AudioStatistics


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
            Group, name=getattr(settings, 'DASHBOARD_FINANCIAL_GROUP', None)
        ) in user_groups
    return (
        'index.html',
        {
            'activity_rows': is_admin or is_seller,
            'is_financial': is_admin or is_financial,
            'financial_extra_items_template': getattr(settings, 'DASHBOARD_FINANCIAL_EXTRA_ITEMS_TEMPLATE', None),
        },
    )


@never_cache
@permission_required('thedaily.change_subscriber')
@to_response
def load_table(request, table_id):

    month = request.GET.get('month')
    year = request.GET.get('year')
    today = date.today()

    if table_id in ('activity', 'activity_only_digital'):
        # Alow only admins or member of seller group
        if not (
            request.user.is_superuser
            or get_object_or_404(
                Group, name=getattr(settings, 'DASHBOARD_SELLER_GROUP', None)
            ) in request.user.groups.all()
        ):
            return HttpResponseForbidden()

    if month and year and table_id not in ('activity', 'activity_only_digital', 'subscribers'):
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
        rows = reader(open(join(settings.DASHBOARD_REPORTS_PATH, filename)))
        if table_id == 'subscribers':
            rows = [(row[:-1] + [row[-1].split(u', ')]) for row in rows if row[1].startswith('%s-%s' % (year, month))]
    except Exception:
        rows = None
    else:
        # TODO: show warning if we know the data for the selected table/date was not generated correctly
        pass

    return (
        'table.html',
        {
            'rows': rows,
            'table_id': table_id,
            'month': month,
            'year': year,
            'date_start': date_start,
            'date_end': date_end,
        },
    )


@never_cache
@permission_required('thedaily.change_subscriber')
def export_csv(request, table_id):
    month = request.GET.get('month')
    year = request.GET.get('year')
    content = open(join(settings.DASHBOARD_REPORTS_PATH, '%s.csv' % table_id))
    if month and year and table_id == 'subscribers':
        resp = HttpResponse(content_type='text/csv')
        w = writer(resp)
        w.writerows([row for row in reader(content) if row[1].startswith('%s-%s' % (year, month))])
    else:
        resp = HttpResponse(content=content.read(), content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename=%s.csv' % table_id
    return resp


@never_cache
@require_POST
def audio_statistics_api(request):
    subscriber_id = request.POST.get('subscriber_id')
    audio_id = request.POST.get('audio_id')
    percentage = int(request.POST.get('percentage'))

    if not (
        subscriber_id
        or AudioStatistics.objects.filter(
            subscriber_id=subscriber_id, audio_id=audio_id, percentage__lte=percentage
        ).exists()
    ):
        return HttpResponse()
    else:
        try:
            audio_statistics, created = AudioStatistics.objects.get_or_create(
                subscriber_id=subscriber_id, audio_id=audio_id
            )
            if audio_statistics.percentage < percentage:
                audio_statistics.percentage = percentage
                audio_statistics.save()
                return HttpResponse()
            return HttpResponse()
        except ValidationError:
            raise HttpResponseBadRequest("Unique object already exists")


@never_cache
@csrf_exempt
@require_POST
def audio_statistics_api_amp(request):

    if not hasattr(request.user, 'subscriber'):
        return HttpResponseForbidden()

    subscriber_id = request.user.subscriber.id
    audio_id = request.GET.get('audio_id')

    if AudioStatistics.objects.filter(subscriber_id=subscriber_id, audio_id=audio_id, amp_click=True).exists():
        return HttpResponse()
    else:
        try:
            audio_statistics, created = AudioStatistics.objects.get_or_create(
                subscriber_id=subscriber_id, audio_id=audio_id
            )
            audio_statistics.amp_click = True
            audio_statistics.save()
            return HttpResponse()
        except ValidationError:
            raise HttpResponseBadRequest("Unique object already exists")
