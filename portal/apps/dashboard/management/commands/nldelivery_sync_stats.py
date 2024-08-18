""" Adapted from: A simple example of how to access the Google Analytics API. """

import sys
import time
import logging

from google.oauth2 import service_account
from google.analytics import data_v1beta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now, datetime, timedelta

from dashboard.models import NewsletterDelivery


def get_report(event_name, start_date, end_date, campaign, delivery_date, limit=None):

    credentials = service_account.Credentials.from_service_account_file(settings.DASHBOARD_GA_SECRETS)
    client = data_v1beta.BetaAnalyticsDataClient(credentials=credentials)
    request = data_v1beta.RunReportRequest(
        property="properties/" + settings.DASHBOARD_GA_PROPERTY,
        dimensions=[
            {'name': "eventName"},
            {"name": "customEvent:campaign"},
            {"name": "customEvent:date"},
            {"name": "customEvent:subscriber_id"},
        ],
        metrics=[{"name": "eventCount"}],
        date_ranges=[{"start_date": start_date, "end_date": end_date}],
        limit=limit,
        dimension_filter={
            "and_group": {
                "expressions": [
                    {
                        "filter": {
                            "field_name": "eventName",
                            "string_filter": {"match_type": "EXACT", "value": event_name, "case_sensitive": True},
                        }
                    },
                    {
                        "filter": {
                            "field_name": "customEvent:campaign",
                            "string_filter": {"match_type": "EXACT", "value": campaign, "case_sensitive": True},
                        }
                    },
                    {
                        "filter": {
                            "field_name": "customEvent:date",
                            "string_filter": {"match_type": "EXACT", "value": delivery_date, "case_sensitive": True},
                        }
                    },
                ]
            }
        },
    )
    return client.run_report(request=request)


class Command(BaseCommand):
    help = 'Updates Newsletter Delivery statistics with the events data collected from Google Analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            action='store',
            type=str,
            dest='start_date',
            default="2daysAgo",
            help="Get data since this date, format: any string valid in GA reports. (default='2daysAgo')",
        )
        parser.add_argument(
            '--end-date',
            action='store',
            type=str,
            dest='end_date',
            default="today",
            help="Get data until this date, format: any string valid in GA reports. (default='today')",
        )
        parser.add_argument(
            '--campaign',
            action='store',
            type=str,
            dest='campaign',
            help='Get Google Analytics stats only for this campaign, default=all campaigns delievered on start-date',
        )
        parser.add_argument(
            '--no-sync', action='store_true', default=False, dest='no_sync', help='No sync, only print'
        )

    def handle(self, *args, **options):

        start_date, end_date, verbosity = options.get('start_date'), options.get('end_date'), options.get('verbosity')
        campaign_arg, empty_count, no_sync = options.get('campaign'), 0, options.get('no_sync')
        today = now().date()

        # log
        log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
        log = logging.getLogger(__name__)
        log.setLevel(logging.DEBUG)
        if settings.DEBUG or verbosity > 1:
            # print also to stdout
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setLevel(logging.DEBUG)
            stdout_handler.setFormatter(log_formatter)
            log.addHandler(stdout_handler)
        if not settings.DEBUG:
            # print also errors to stderr to receive cron alert
            err_handler = logging.StreamHandler(sys.stderr)
            err_handler.setLevel(logging.ERROR)
            err_handler.setFormatter(log_formatter)
            log.addHandler(err_handler)
        logfile = getattr(settings, "DASHBOARD_NLDELIVERY_SYNC_STATS_LOGFILE", None)
        if logfile:
            h = logging.FileHandler(filename=logfile)
            h.setFormatter(log_formatter)
            log.addHandler(h)

        if not (hasattr(settings, "DASHBOARD_GA_PROPERTY") and hasattr(settings, "DASHBOARD_GA_SECRETS")):
            log.error('No Google Analytics property or secrets json file are configured in settings.')

        filter_kwargs = {}
        if campaign_arg:
            campaigns = [campaign_arg]
            filter_kwargs = {"newsletter_name": campaign_arg}
        if start_date == "today":
            delivery_date = today
        elif start_date == "yesterday":
            delivery_date = today - timedelta(1)
        elif start_date.endswith("daysAgo"):
            delivery_date = today - timedelta(int(start_date[0]))
        else:
            delivery_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        filter_kwargs["delivery_date"] = delivery_date
        campaigns = NewsletterDelivery.objects.filter(
            **filter_kwargs
        ).values_list("newsletter_name", flat=True).distinct()

        delivery_date_formatted = delivery_date.strftime("%Y%m%d")
        for campaign in campaigns:
            for event_name in ['open_email_r', 'open_email_s']:
                response = get_report(event_name, start_date, end_date, campaign, delivery_date_formatted, 1)

                try:
                    rows = response.row_count
                    assert rows > 0
                except (KeyError, IndexError, AssertionError):
                    empty_count += 1
                    continue

                if verbosity > 0:
                    log.info('%s, %s, %s: %s' % (campaign, delivery_date_formatted, event_name, rows))

                if not no_sync:
                    try:
                        nl_delivery = NewsletterDelivery.objects.get(
                            newsletter_name=campaign, delivery_date=delivery_date
                        )
                        if event_name == 'open_email_r':
                            nl_delivery.user_opened = rows
                        else:
                            nl_delivery.subscriber_opened = rows
                        nl_delivery.save()
                    except NewsletterDelivery.DoesNotExist:
                        pass

                time.sleep(1)  # wait a bit to be polite with GA api

        if empty_count == len(campaigns) * 2:
            log.error('No data could be found')
