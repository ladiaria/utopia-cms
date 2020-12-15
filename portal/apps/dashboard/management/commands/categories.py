# -*- coding: utf-8 -*-

"""
Note: output from this command is not used in the dashboard view
"""

from os.path import join
from unicodecsv import writer

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Category


def generate_report(category_slug):
    c = Category.objects.get(slug=category_slug)
    w = writer(open(join(
        settings.DASHBOARD_REPORTS_PATH,
        'category_%s.csv' % category_slug), 'w')
    )
    w.writerow(['url', 'título', 'fecha', 'caracteres'])
    for s in c.section_set.iterator():
        for a in s.articles_core.iterator():
            w.writerow([
                a.get_absolute_url(), a.headline, a.date_published.date(),
                len(a.body)])


class Command(BaseCommand):
    help = 'Generates categories articles report content'

    def handle(self, *args, **options):
        for category_slug in ('cultura', 'cotidiana', 'politica'):
            generate_report(category_slug)
