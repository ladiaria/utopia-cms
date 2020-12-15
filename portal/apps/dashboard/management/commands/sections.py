# -*- coding: utf-8 -*-

"""
Note: output from this command is not used in the dashboard view
"""

from os.path import join
from unicodecsv import writer

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Section


def generate_report(section_name):
    s = Section.objects.get(name=section_name)
    w = writer(open(join(
        settings.DASHBOARD_REPORTS_PATH, 'section_%s.csv' % section_name), 'w')
    )
    w.writerow(['url', 'título', 'fecha', 'caracteres'])
    for a in s.articles_core.iterator():
        w.writerow([
            a.get_absolute_url(), a.headline, a.date_published.date(),
            len(a.body)])


class Command(BaseCommand):
    help = 'Generates sections articles report content'

    def handle(self, *args, **options):
        for section_name in ('Posturas', 'Humor'):
            generate_report(section_name)
