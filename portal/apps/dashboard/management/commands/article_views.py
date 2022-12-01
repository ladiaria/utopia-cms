from __future__ import division

import os
from os.path import join
from csv import writer
from datetime import datetime, date, timedelta
from progress.bar import Bar

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Sum

from core.models import Article


class Command(BaseCommand):
    help = 'Generates the articles views report sorted by category or publication if there \'s not one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--progress', action='store_true', default=False, dest='progress', help='Show a progress bar'
        )
        parser.add_argument(
            '--subscribers-only',
            action='store_true',
            default=False,
            dest='subscribers-only',
            help='Show only subscribers on the file',
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
        subscribers_only = options.get("subscribers-only")
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
            index_object = None
            if article.main_section and article.main_section.section.slug in getattr(
                settings, 'DASHBOARD_MAIN_SECTION_SLUGS', []
            ):
                index_object = article.main_section.section
            elif article.main_section and article.main_section.section and article.main_section.section.category:
                index_object = article.main_section.section.category
            elif (
                article.main_section
                and article.main_section.edition.publication
                and article.main_section.edition.publication.slug
                not in getattr(settings, 'DASHBOARD_EXCLUDE_PUBLICATION_SLUGS', [])
            ):
                index_object = article.main_section.edition.publication
            if index_object:
                views, articles_count, unique_viewers = articles_views.get(index_object, (0, 0, []))
                if subscribers_only:
                    for av in article.articleviewedby_set.all().select_related('user', 'user__subscriber'):
                        if av.user.subscriber and av.user.subscriber.is_subscriber():
                            views += 1
                            if av.user.id not in unique_viewers:
                                unique_viewers.append(av.user.id)
                else:
                    views += article.articleviews_set.all().aggregate(v=Sum('views'))['v']
                articles_count += 1
                articles_views[index_object] = (views, articles_count, unique_viewers)
            if bar:
                bar.next()
        if bar:
            bar.finish()

        sorted_dict = sorted(articles_views.items(), key=lambda item: item[1], reverse=True)
        suffix = "_subscribers_only" if subscribers_only else ""
        if not out_prefix:
            try:
                os.rename(
                    join(settings.DASHBOARD_REPORTS_PATH, f"article_views{suffix}.csv"),
                    join(
                        settings.DASHBOARD_REPORTS_PATH,
                        f"{month_before_last.year}{month_before_last.month:02d}_article_views{suffix}.csv",
                    ),
                )
            except FileNotFoundError:
                pass
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, f"{out_prefix}article_views{suffix}.csv"), "w"))
        i = 0
        for category_or_publication, item in sorted_dict:
            i += 1
            views = item[0]
            articles_count = item[1]
            if subscribers_only:
                unique_viewers = len(item[2])
                w.writerow(
                    [
                        i,
                        category_or_publication.name,
                        articles_count,
                        unique_viewers,
                        views,
                        views / (articles_count or 1),
                    ]
                )
            else:
                w.writerow(
                    [
                        i,
                        category_or_publication.name,
                        articles_count,
                        views,
                        views / (articles_count or 1),
                    ]
                )
