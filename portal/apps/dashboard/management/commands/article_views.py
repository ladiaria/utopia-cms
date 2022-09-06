from __future__ import division

import os
from os.path import join
from csv import writer
from datetime import datetime, date, timedelta
from progress.bar import Bar

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Article

class Command(BaseCommand):
    help = 'Generates the articles views report sorted by category or publication if there \'s not one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--progress', action='store_true', default=False, dest='progress', help='Show a progress bar'
        )
        parser.add_argument(
            '--out-prefix',
            action='store',
            type=str,
            dest='out-prefix',
            default='',
            help="Don't make changes to existing files and save generated files with this prefix",
        )

    def handle(self, *args, **options):
        articles_views, out_prefix = {}, options.get('out-prefix')
        this_month_first = date.today().replace(day=1)
        last_month = this_month_first - timedelta(1)
        last_month_first = datetime.combine(last_month.replace(day=1), datetime.min.time())
        month_before_last = last_month_first - timedelta(1)
        dt_until = datetime.combine(this_month_first, datetime.min.time())
        verbosity = options.get('verbosity')
        if verbosity > 1:
            print('Generating reports from %s to %s ...' % (last_month_first, dt_until))

        articles = Article.objects.filter(
            date_published__gte=last_month_first,
            date_published__lte=dt_until,
        )

        bar = Bar('Processing', max=articles.count()) if options.get('progress') else None

        for article in articles.iterator():
            if article.main_section and article.main_section.section and article.main_section.section.category:
                views, articles_count = articles_views.get(article.main_section.section.category, (0, 0))
                views += article.articleviews_set.count()
                articles_count += 1
                articles_views[article.main_section.section.category] = (views, articles_count)
            elif(
                article.main_section and article.main_section.edition.publication and
                    article.main_section.edition.publication.slug not in
                    getattr(settings, 'DASHBOARD_EXCLUDE_PUBLICATION_SLUGS', [])):
                views, articles_count = articles_views.get(article.main_section.edition.publication, (0, 0))
                views += article.articleviews_set.count()
                articles_count += 1
                articles_views[article.main_section.edition.publication] = (views, articles_count)
            if bar:
                bar.next()
        if bar:
            bar.finish()

        sorted_dict = sorted(articles_views.items(), key=lambda item: item[1], reverse=True)
        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, 'article_views.csv'),
                join(
                    settings.DASHBOARD_REPORTS_PATH, '%s%.2d_article_views.csv' % (
                        month_before_last.year, month_before_last.month
                    )
                ),
            )
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '%sarticle_views.csv' % out_prefix), 'w'))
        i = 0
        for category_or_publication, item in sorted_dict:
            i += 1
            views = item[0]
            articles_count = item[1]

            w.writerow([
                i,
                category_or_publication.name,
                articles_count,
                views,
                views / (articles_count or 1),
            ])
