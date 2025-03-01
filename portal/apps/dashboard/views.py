# coding=utf-8

from os.path import join
from csv import reader, writer
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
from django.utils.timezone import now, datetime

from django_amp_readerid.utils import get_related_user

from core.models import Publication
from thedaily.utils import get_profile_newsletters_ordered
from .management.commands.nldelivery_sync_stats import get_report
from .models import AudioStatistics, NewsletterDelivery


to_response = render_response('dashboard/templates/')


@never_cache
@permission_required('thedaily.change_subscriber')
@to_response
def index(request):
    is_admin, is_seller, is_financial = request.user.is_superuser, False, False
    if not is_admin:
        user_groups = request.user.groups.all()
        is_seller = get_object_or_404(Group, name=getattr(settings, 'DASHBOARD_SELLER_GROUP', None)) in user_groups
        is_financial = (
            get_object_or_404(Group, name=getattr(settings, 'DASHBOARD_FINANCIAL_GROUP', None)) in user_groups
        )
    return (
        'index.html',
        {
            'activity_rows': is_admin or is_seller,
            'is_financial': is_admin or is_financial,
            'financial_extra_items_template': getattr(settings, 'DASHBOARD_FINANCIAL_EXTRA_ITEMS_TEMPLATE', None),
            "newsletters": get_profile_newsletters_ordered(),
            "site_url": '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN),
            "multi_publication": Publication.multi(),
        },
    )


@never_cache
@permission_required('thedaily.change_subscriber')
@to_response
def load_table(request, table_id):

    month, year, today = request.GET.get('month'), request.GET.get('year'), now().date()
    context = {'month': month, 'year': year}

    if table_id in ('activity', 'activity_only_digital'):
        # Alow only admins or member of seller group
        if (
            request.user.is_superuser
            or get_object_or_404(Group, name=getattr(settings, 'DASHBOARD_SELLER_GROUP', None))
            in request.user.groups.all()
        ):
            context['extra_columns'] = getattr(settings, 'DASHBOARD_ACTIVITY_EXTRA_COLUMNS', [])
        else:
            return HttpResponseForbidden()

    if month and year and table_id not in ('activity', 'activity_only_digital', 'subscribers'):
        date_start = datetime(int(year), int(month), 1).date()
        date_end = date_start + relativedelta(months=1)
        last_month = today - relativedelta(months=1)
        if int(month) == last_month.month and int(year) == last_month.year:
            filename = '%s.csv' % table_id
        else:
            filename = '%s%s_%s.csv' % (year, month, table_id)
    else:
        date_end = datetime(today.year, today.month, 1).date()
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

    if settings.DEBUG:
        print('DEBUG: audio_statistics_api %% received: %s' % percentage)

    if subscriber_id and audio_id:
        audio_statistics, created = AudioStatistics.objects.get_or_create(
            subscriber_id=subscriber_id, audio_id=audio_id
        )
        if percentage and (audio_statistics.percentage or 0) < percentage:
            audio_statistics.percentage = percentage
            audio_statistics.save()

    return HttpResponse()


@never_cache
@csrf_exempt
@require_POST
def audio_statistics_api_amp(request):

    user = get_related_user(request, use_body=True)

    if not hasattr(user, 'subscriber'):
        return HttpResponseForbidden()

    subscriber_id = user.subscriber.id
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
            return HttpResponseBadRequest("Unique object already exists")


@never_cache
def nl_open(request, nl_delivery_id, nl_delivery_segment):
    nl_delivery_obj = get_object_or_404(NewsletterDelivery, id=nl_delivery_id)
    ga4_response = get_report(
        "open_email" + ("_s" if nl_delivery_segment == "subscriber" else "_r"),
        str(nl_delivery_obj.delivery_date),
        "today",
        nl_delivery_obj.newsletter_name,
        nl_delivery_obj.delivery_date.strftime("%Y%m%d"),
        int(getattr(nl_delivery_obj, nl_delivery_segment + "_opened") * 1.5),  # limit rows to 50% more
    )
    rows = getattr(ga4_response, "rows", [])
    if rows:
        response = HttpResponse(content_type="text/csv")
        w = writer(response)
        w.writerows([r.dimension_values[-1].value] for r in rows)
        response['Content-Disposition'] = 'attachment; filename=nlopen_%s_%s.csv' % (
            nl_delivery_id, nl_delivery_segment
        )
    else:
        response = HttpResponse()
    return response
