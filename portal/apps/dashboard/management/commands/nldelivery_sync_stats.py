""" Adapted from: A simple example of how to access the Google Analytics API. """
from __future__ import print_function
from __future__ import unicode_literals

import sys
import time
from datetime import date

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from progress.bar import Bar

from dashboard.models import NewsletterDelivery

from django.conf import settings
from django.core.management.base import BaseCommand


def initialize_analyticsreporting():
    """
    Initializes an Analytics Reporting API V4 service object.

    Returns:
    An authorized Analytics Reporting API V4 service object.
    """
    try:
        KEY_FILE_LOCATION = settings.DASHBOARD_GA_SECRETS
    except AttributeError:
        sys.exit('ERROR: No secrets file configured in settings.')
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        KEY_FILE_LOCATION, ['https://www.googleapis.com/auth/analytics.readonly']
    )

    # Build the service object.
    analytics = build('analyticsreporting', 'v4', credentials=credentials)

    return analytics


def get_report(analytics, start_date, end_date, campaign, delivery_date):
    """
    Queries the Analytics Reporting API V4.

      Args:
        analytics: An authorized Analytics Reporting API V4 service object.
      Returns:
        The Analytics Reporting API V4 response.
    """
    try:
        VIEW_ID = settings.DASHBOARD_GA_VIEW_ID
    except AttributeError:
        sys.exit('ERROR: No view id configured in settings.')

    # startDate can be also in format XdaysAgo (example: 2daysAgo)
    # TODO: investigate sessions vs totalEvents vs uniqueEvents
    request_data = {
        'viewId': VIEW_ID,
        'dateRanges': [{'startDate': start_date or 'yesterday', 'endDate': end_date or 'yesterday'}],
        # 'metrics': [{'expression': 'ga:sessions'}],
        # 'metrics': [{'expression': 'ga:totalEvents'}],
        'metrics': [{'expression': 'ga:uniqueEvents'}],
        'dimensions': [
            {'name': 'ga:eventLabel'},
            {'name': 'ga:campaign'},
            {'name': 'ga:pageTitle'},
            # {'name': 'ga:date'},
            # {'name': 'ga:hour'},
            # {'name': 'ga:minute'},
        ],
        'dimensionFilterClauses': [
            {
                "operator": "AND",
                "filters": [
                    {"dimensionName": "ga:campaign", "operator": "EXACT", "expressions": [campaign]},
                    {
                        "dimensionName": "ga:pageTitle",
                        "not": not delivery_date,
                        "operator": "EXACT",
                        "expressions": [delivery_date or '(not set)'],
                    },
                    {
                        "dimensionName": "ga:eventLabel",
                        "operator": "IN_LIST",
                        "expressions": ['open_email', 'open_email_s'],
                    },
                ],
            },
        ],
    }

    return analytics.reports().batchGet(body={'reportRequests': [request_data]}).execute()


class Command(BaseCommand):
    help = 'Updates Newsletter Delivery statistics with the events data collected from Google Analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            action='store',
            type=str,
            dest='start_date',
            help='Get Google Analytics stats from this date, default=yesterday',
        )
        parser.add_argument(
            '--end-date',
            action='store',
            type=str,
            dest='end_date',
            help='Get Google Analytics stats until this date, default=yesterday',
        )
        parser.add_argument(
            '--campaign',
            action='store',
            type=str,
            dest='campaign',
            help='Get Google Analytics stats only for this campaign, default=all campaigns within 12 months',
        )
        parser.add_argument(
            '--delivery-date',
            action='store',
            type=str,
            dest='delivery_date',
            help='Get Google Analytics stats only for this delivery date (campaign also must be given)',
        )
        parser.add_argument(
            '--progress', action='store_true', default=False, dest='progress', help='Show a progress bar'
        )
        parser.add_argument(
            '--no-sync', action='store_true', default=False, dest='no_sync', help='No sync, only print'
        )
        parser.add_argument(
            '--sync-rangeonly',
            action='store_true',
            default=False,
            dest='sync_rangeonly',
            help='Only sync campaign objects if delivery date is in the custom date range that must be given',
        )

    def handle(self, *args, **options):
        analytics = initialize_analyticsreporting()
        start_date, end_date = options.get('start_date'), options.get('end_date')
        campaign_arg, today, empty_count = options.get('campaign'), date.today(), 0
        delivery_date = options.get("delivery_date")

        if campaign_arg:
            campaigns = [campaign_arg]
        else:
            if delivery_date:
                sys.exit("ERROR: To pick one delivery date stat, campaign must also be given")
            campaigns = NewsletterDelivery.objects.filter(
                delivery_date__gte=date(today.year - 1, today.month, 1)
            ).values_list("newsletter_name", flat=True).distinct()

        # divide api calls into campaigns to lower the prob. to obtain limited 1000 rows results, otherwise pagination
        # should be implemented.
        for campaign in campaigns:
            response = get_report(analytics, start_date, end_date, campaign, delivery_date)
            try:
                rows = response['reports'][0]['data']['rows']
            except (KeyError, IndexError):
                empty_count += 1
                continue
            else:
                bar = Bar('Processing "%s" \tresults:' % campaign, max=len(rows)) if options.get('progress') else None

            no_sync = options.get('no_sync')
            sync_rangeonly = start_date and end_date and options.get('sync_rangeonly')

            for row in rows:
                if bar:
                    bar.next()

                # NOTE: date, hour, minute can help to debug:
                # event_label, campaign, page_title, ga_date, ga_hour, ga_minute = row['dimensions']

                event_label, campaign, page_title = row['dimensions']
                count = row['metrics'][0]['values'][0]

                if sync_rangeonly and (page_title < start_date or page_title > end_date):
                    continue
                if no_sync:
                    print('%s, %s, %s: %s' % (campaign, page_title, event_label, count))
                    """
                    print(
                        '%s, %s, %s, %s %s:%s : %s' % (
                            campaign, page_title, event_label, ga_date, ga_hour, ga_minute, count
                        )
                    )
                    """
                else:
                    try:
                        nl_delivery = NewsletterDelivery.objects.get(newsletter_name=campaign, delivery_date=page_title)
                        if event_label == 'open_email':
                            nl_delivery.user_opened = (nl_delivery.user_opened or 0) + int(count)
                        else:
                            nl_delivery.subscriber_opened = (nl_delivery.subscriber_opened or 0) + int(count)
                        nl_delivery.save()
                    except NewsletterDelivery.DoesNotExist:
                        pass

            if bar:
                bar.finish()

            time.sleep(1)  # wait a bit to be polite

        if empty_count == len(campaigns):
            print('ERROR: No data could be found')
