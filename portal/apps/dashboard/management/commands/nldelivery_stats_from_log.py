import re
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dashboard.models import NewsletterDelivery


class Command(BaseCommand):
    help = 'Get (and update if indicated) Newsletter Delivery statistics from the lines on its log delivery file'

    def add_arguments(self, parser):
        parser.add_argument('newsletter_name', nargs=1, type=str, help='The newsletter name to identify its log file')
        parser.add_argument(
            'delivery_date',
            nargs=1,
            type=str,
            help='The delivery date of the NL to identify its log file, format: YYYYMMDD',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            default=False,
            dest='update',
            help='Update the stored stats object with the values obtained from the log'
        )
        parser.add_argument(
            '--newsletter-campaign',
            action='store',
            type=str,
            dest='newsletter_campaign',
            help='The newsletter campaign to identify the delivery object to update (defaults to newsletter-name)',
        )

    def handle(self, *args, **options):
        delivery_date, newsletter_name = options.get('delivery_date')[0], options.get('newsletter_name')[0]
        stats_found_collector = {"user_sent": 0, "subscriber_sent": 0}
        stat_keys = stats_found_collector.keys()
        try:
            for line in open(settings.SENDNEWSLETTER_LOGFILE % (newsletter_name, delivery_date)).readlines():
                for k in stat_keys:
                    found = re.search(r'%s: (\d+)' % k, line)
                    if found:
                        stats_found_collector[k] += int(found.groups()[0])
                    else:
                        break
            print(stats_found_collector)
            if options.get("update"):
                try:
                    nl_delivery = NewsletterDelivery.objects.get(
                        delivery_date=datetime.strptime(delivery_date, "%Y%m%d").date(),
                        newsletter_name=options.get('newsletter_campaign') or newsletter_name,
                    )
                    save = False
                    for k, v in stats_found_collector.items():
                        if getattr(nl_delivery, k) != v:
                            save = True
                            setattr(nl_delivery, k, v)
                    if save:
                        nl_delivery.save()
                except NewsletterDelivery.DoesNotExist:
                    raise CommandError("stats object not found for update")
                else:
                    print("stat object %s" % ("updated" if save else "unchanged"))
        except IOError:
            raise CommandError("log file not found")
