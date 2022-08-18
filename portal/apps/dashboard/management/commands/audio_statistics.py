# -*- coding: utf-8 -*-
import os
from os.path import join
from csv import writer
from datetime import date, datetime, timedelta

from progress.bar import Bar

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from core.models import Article


class Command(BaseCommand):
    """
    NOTE: more precise information about how to split the stats in time is needed (weeks? months? years?).
          this should be done because the generated CSV can be heavy to load if it has the full-time stats content.
    """
    help = 'Writes audio stats to CSV'

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
        parser.add_argument(
            '--from-date',
            action='store',
            type=str,
            dest='from-date',
            help='Use a custom from date to filter articles, default=1st day of last month',
        )
        parser.add_argument(
            '--to-date',
            action='store',
            type=str,
            dest='to-date',
            help='Use a custom to date to filter articles, default=1st day of this month',
        )

    def handle(self, *args, **options):
        out_prefix, from_date, to_date = options.get('out-prefix'), options.get('from-date'), options.get('to-date')

        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
            except ValueError:
                raise CommandError('from-date given has invalid format')
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                raise CommandError('to-date given has invalid format')

        if (from_date or to_date) and not out_prefix:
            raise CommandError('out-prefix should be given when any filter date option is given')

        this_month_first = date.today().replace(day=1)
        last_month = this_month_first - timedelta(1)
        last_month_first = datetime.combine(last_month.replace(day=1), datetime.min.time())
        month_before_last = last_month_first - timedelta(1)
        dt_until = datetime.combine(this_month_first, datetime.min.time())

        articles = Article.published.filter(
            audio__isnull=False,
            date_published__gte=from_date or last_month_first, date_published__lte=to_date or dt_until,
        ).select_related('main_section__section', 'audio').prefetch_related('audio__audiostatistics').distinct()
        bar = Bar('Processing', max=articles.count()) if options.get('progress') else None

        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, 'audio_statistics.csv'),
                join(
                    settings.DASHBOARD_REPORTS_PATH,
                    '%s%.2d_audio_statistics.csv' % (month_before_last.year, month_before_last.month),
                ),
            )

        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '{}audio_statistics.csv'.format(out_prefix)), 'w'))
        for article in articles.iterator():
            # TODO: duration calculation disabled, it raises a UnicodeDecodeError and should be investigated.
            # audio_info = mutagen.File(article.audio.file).info; duration = timedelta(seconds=int(audio_info.length))
            w.writerow(
                [
                    article.headline,
                    article.get_absolute_url(),
                    article.section,
                    article.date_published,
                    article.audio.audiostatistics_set.filter(percentage__isnull=False).count(),
                    article.audio.audiostatistics_set.filter(amp_click=True).count(),
                    article.audio.audiostatistics_set.filter(percentage=0).count(),
                    article.audio.audiostatistics_set.filter(percentage=25).count(),
                    article.audio.audiostatistics_set.filter(percentage=50).count(),
                    article.audio.audiostatistics_set.filter(percentage=75).count(),
                ]
            )
            if bar:
                bar.next()
        if bar:
            bar.finish()
