# -*- coding: utf-8 -*-
from os.path import join
from unicodecsv import writer
from progress.bar import Bar
from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User

from thedaily.management.commands.automatic_mail import latest_activity


class Command(BaseCommand):
    help = 'Generates the activity report content'

    option_list = BaseCommand.option_list + (
        make_option('--progress', action='store_true', default=False, dest='progress', help=u'Show a progress bar'), )

    def handle(self, *args, **options):

        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, 'activity.csv'), 'w'))
        no_staff_users = User.objects.select_related('subscriber').filter(is_staff=False, subscriber__isnull=False)
        bar = Bar('Processing', max=no_staff_users.count()) if options.get('progress') else None

        for u in no_staff_users.iterator():

            if bar:
                bar.next()

            if u.subscriber.is_subscriber():
                w.writerow([
                    u.get_full_name() or u.username, u.email, u.date_joined, u.is_active, latest_activity(u)])

        if bar:
            bar.finish()
