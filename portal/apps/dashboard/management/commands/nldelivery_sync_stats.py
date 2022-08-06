""" Adapted from: A simple example of how to access the Google Analytics API. """
from __future__ import print_function
from __future__ import unicode_literals
import sys
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
        sys.exit(u'ERROR: No secrets file configured in settings.')
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        KEY_FILE_LOCATION, ['https://www.googleapis.com/auth/analytics.readonly']
    )

    # Build the service object.
    analytics = build('analyticsreporting', 'v4', credentials=credentials)

    return analytics


def get_report(analytics, start_date, end_date, campaign):
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
        sys.exit(u'ERROR: No view id configured in settings.')

    # startDate can be also in format XdaysAgo (example: 2daysAgo)
    # TODO: investigate sessions vs totalEvents vs uniqueEvents
    request_data = {
        'viewId': VIEW_ID, 'dateRanges': [{'startDate': start_date or 'yesterday', 'endDate': end_date or 'today'}],
        # 'metrics': [{'expression': 'ga:sessions'}],
        # 'metrics': [{'expression': 'ga:totalEvents'}],
        'metrics': [{'expression': 'ga:uniqueEvents'}],
        'dimensions': [
            {'name': 'ga:eventLabel'}, {'name': 'ga:campaign'}, {'name': 'ga:pageTitle'},
            # {'name': 'ga:date'}, {'name': 'ga:hour'}, {'name': 'ga:minute'}
        ],
        'dimensionFilterClauses': [
            {
                "operator": "AND",
                "filters": [
                    {"dimensionName": "ga:pageTitle", "not": True, "operator": "EXACT", "expressions": ['(not set)']},
                    {"dimensionName": "ga:eventLabel", "operator": "BEGINS_WITH", "expressions": ['open_email']}
                ],
            },
        ],
    }

    campaign_filter = {"dimensionName": "ga:campaign", "operator": "EXACT", "expressions": [campaign or '(not set)']}

    if not campaign:
        campaign_filter['not'] = True

    request_data["dimensionFilterClauses"][0]['filters'].append(campaign_filter)

    return analytics.reports().batchGet(body={'reportRequests': [request_data]}).execute()


class Command(BaseCommand):
    help = u'Updates Newsletter Delivery statistics with the events data collected from Google Analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            action='store',
            type=str,
            dest='start_date',
            help=u'Get Google Analytics stats from this date, default=yesterday',
        )
        parser.add_argument(
            '--end-date',
            action='store',
            type=str,
            dest='end_date',
            help=u'Get Google Analytics stats until this date, default=today',
        )
        parser.add_argument(
            '--campaign',
            action='store',
            type=str,
            dest='campaign',
            help=u'Get Google Analytics stats only for this campaign, default=all',
        )
        parser.add_argument(
            '--progress', action='store_true', default=False, dest='progress', help=u'Show a progress bar'
        )
        parser.add_argument(
            '--no-sync', action='store_true', default=False, dest='no_sync', help=u'No sync, only print'
        )

    def handle(self, *args, **options):
        analytics = initialize_analyticsreporting()
        response = get_report(analytics, options.get('start_date'), options.get('end_date'), options.get('campaign'))
        try:
            rows = response['reports'][0]['data']['rows']
        except (KeyError, IndexError):
            sys.exit(u'ERROR: No data could be found')
        else:
            bar = Bar('Processing', max=len(rows)) if options.get('progress') else None

        for row in rows:
            if bar:
                bar.next()

            # TODO: run this command at 00:01 using default dates. date, hour, minute can help to debug
            # event_label, campaign, page_title, ga_date, ga_hour, ga_minute = row['dimensions']

            event_label, campaign, page_title = row['dimensions']
            count = row['metrics'][0]['values'][0]
            if options.get('no_sync'):
                print(u'%s, %s, %s: %s' % (campaign, page_title, event_label, count))
                # print(u'%s, %s, %s, %s %s:%s : %s' % (
                #    campaign, page_title, event_label, ga_date, ga_hour, ga_minute, count))
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
