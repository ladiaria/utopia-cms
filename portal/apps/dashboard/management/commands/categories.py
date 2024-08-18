# -*- coding: utf-8 -*-

"""
Note: output from this command is not used in the dashboard view
"""

from os.path import join
from csv import writer

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Category


def generate_report(category_slug):
    c = Category.objects.get(slug=category_slug)
    w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, 'category_%s.csv' % category_slug), 'w'))
    w.writerow(['url', 'título', 'fecha', 'caracteres'])
    w.writerows([a.get_absolute_url(), a.headline, a.date_published.date(), len(a.body)] for a in c.articles())


class Command(BaseCommand):
    help = 'Generates categories articles report content'

    def add_arguments(self, parser):
        parser.add_argument('categories_slugs', nargs='+', type=str)

    def handle(self, *args, **options):
        for category_slug in options.get('categories_slugs'):
            generate_report(category_slug)
