import csv
import collections
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import OrderedDict

from django.conf import settings
from django.core.management.base import BaseCommand
from thedaily.email_logic import SUBJ_FREE_ARTICLES_LIMIT
from thedaily.models import SubscriberEvent, Subscriber


# 'heavy users' are free user that consume all free articles in a month

class Command(BaseCommand):
    args = '<filename.csv>'
    help = 'Saves into a csv file, the heavy users from actual month and ' + \
        'last three monthts. Example: If run on 15th April takes users' + \
        'since 1st Jan.'

    def handle(self, *args, **options):
        if len(args) == 0:
            print('error: filename required')
            print('example: <command_name> jan_to_apr_report.csv')
            return
        file = settings.GENERAL_MANAGEMENT_COMMAND_EXPORT_PATH + args[0]

        today = date.today()
        start = today.replace(day=1) - relativedelta(months=3)

        events = SubscriberEvent.objects.filter(
            date_occurred__gte=start,
            description=SUBJ_FREE_ARTICLES_LIMIT).order_by('date_occurred')

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
            w = csv.writer(f)
            w.writerow(['user id', 'nombre', 'mail',
                        'telefono', 'ultimafecha'])
            rev = collections.OrderedDict(reversed(list(s_dic.items())))
            # reverse so in csv is descending order
            for s in rev.items():
                subscriber = Subscriber.objects.get(pk=s[0])
                user = subscriber.user
                user_id = user.id
                mail = user.email
                name = user.get_full_name() or user.subscriber.name
                phone = "'" + str(subscriber.phone) + "'"
                last_date = s[1]
                # print([user_id, name.encode('utf-8'), mail, phone, last_date])
                w.writerow([user_id, name.encode('utf-8'), mail, phone,
                            last_date])
