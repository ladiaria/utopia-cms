# -*- coding: utf-8 -*-

from os.path import join
from csv import writer

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Article
from thedaily.models import Subscriber
from dashboard.utils import latest_activity


class Command(BaseCommand):
    help = 'Generates a CSV containing some data for all subscribers'

    def handle(self, *args, **options):
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, 'subscriber_data.csv'), 'w'))
        for s in Subscriber.objects.select_related(
            'user', 'newsletters'
        ).filter(user__isnull=False, user__is_staff=False).iterator():
            try:
                viewed_articles = s.user.viewed_articles_core
                viewed_sections = ', '.join(
                    set.union(
                        *[set(a.sections.distinct().values_list('name', flat=True)) for a in viewed_articles.all()]
                    )
                )
            except Article.DoesNotExist:
                viewed_sections = ''
            w.writerow(
                [
                    s.id,
                    s.contact_id,
                    s.user.get_full_name() or s.user.username,
                    s.user.email,
                    s.user.date_joined,
                    s.user.is_active,
                    viewed_sections,
                    latest_activity(s.user),
                    ', '.join(s.newsletters.values_list('name', flat=True)),
                ]
            )
