from __future__ import unicode_literals

from os.path import join
from csv import writer
import collections
from dateutil.relativedelta import relativedelta

from collections import OrderedDict

from django.conf import settings
from django.core.management.base import BaseCommand
from thedaily.email_logic import DESC_FREE_ARTICLES_LIMIT
from thedaily.models import SubscriberEvent, Subscriber
from django.utils.timezone import now

# 'heavy users' are free user that consume all free articles in a month


class Command(BaseCommand):
    help = """
        Saves into a csv file, the heavy users from actual month and last three monthts.
        Example: If run on 15th April takes users since 1st Jan.
    """

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs=1, type=str)

    def handle(self, *args, **options):
        file = join(getattr(settings, 'GENERAL_MANAGEMENT_COMMAND_EXPORT_PATH', '/tmp'), options.get('filename')[0])

        today = now().date()
        start = today.replace(day=1) - relativedelta(months=3)

        events = SubscriberEvent.objects.filter(
            date_occurred__gte=start, description=DESC_FREE_ARTICLES_LIMIT
        ).order_by('date_occurred')

        # by construction, if the subscribear repeats, the last is valid

        s_dic = OrderedDict()
        for event in events:
            s_id = event.subscriber_id
            occurred = event.date_occurred
            if s_id in s_dic:
                # when reinserting element it will ve moved to last position
                _ = s_dic.pop(s_id)
            s_dic[s_id] = occurred

        with open(file, 'w') as f:
            w = writer(f)
            w.writerow(['subscriber_id', 'name', 'email', 'telephone', 'last_date'])
            rev = collections.OrderedDict(reversed(list(s_dic.items())))
            # reverse so in csv is descending order
            for s in list(rev.items()):
                subscriber = Subscriber.objects.get(pk=s[0])
                user = subscriber.user
                w.writerow(
                    [subscriber.id, user.get_full_name() or user.subscriber.name, user.email, subscriber.phone, s[1]]
                )
