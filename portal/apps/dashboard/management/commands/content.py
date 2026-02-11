# -*- coding: utf-8 -*-
from os.path import join
from csv import writer
from progress.bar import Bar
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Article


def generate_report(year, progress):
    articles = Article.published.filter(date_published__year=year, main_section__isnull=False)
    bar, content = Bar('Processing', max=articles.count()) if progress else None, {}
    for a in articles.iterator():
        month = a.date_published.month
        publication = a.main_section.edition.publication
        section = a.main_section.section
        total_articles, total_chars = content.get((month, publication, section), [0, 0])
        total_articles += 1
        total_chars += len(a.body)
        content[(month, publication, section)] = [total_articles, total_chars]
        if bar:
            bar.next()
    if bar:
        bar.finish()
    w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, 'content_%s.csv' % year), 'w'))
    w.writerow(['month', 'publication', 'section', 'total articles', 'total chars'])
    w.writerows(list(k) + v for k, v in content.items())


class Command(BaseCommand):
    help = 'Generates a content report with articles and chars published by month and section'

    option_list = BaseCommand.option_list + (
        make_option(
            '--progress', action='store_true', default=False, dest='progress', help=u'Show a progress bar'),
    )

    # TODO: argument for years
    def handle(self, *args, **options):
        for year in (2018, 2019, 2020, ):
            generate_report(year, options.get('progress'))
