# -*- coding: utf-8 -*-
import os
from os.path import join
from unicodecsv import writer
from datetime import date, datetime, timedelta

from progress.bar import Bar

from django.core.management.base import BaseCommand
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
            '--progress', action='store_true', default=False, dest='progress', help=u'Show a progress bar'
        )

        parser.add_argument(
            '--out-prefix',
            action='store',
            type=unicode,  # noqa
            dest='out-prefix',
            default=u'',
            help=u"Don't make changes to existing files and save generated files with this prefix",
        )

    def handle(self, *args, **options):
        out_prefix = options.get('out-prefix')
        this_month_first = date.today().replace(day=1)
        last_month = this_month_first - timedelta(1)
        last_month_first = datetime.combine(last_month.replace(day=1), datetime.min.time())
        month_before_last = last_month_first - timedelta(1)
        dt_until = datetime.combine(this_month_first, datetime.min.time())

        articles = Article.published.filter(
            audio__isnull=False,
            date_published__gte=last_month_first,
            date_published__lte=dt_until).select_related('main_section__section', 'audio').prefetch_related(
                'audio__audiostatistics').distinct()
        bar = Bar('Processing', max=articles.count()) if options.get('progress') else None

        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, 'audio_statistics.csv'),
                join(
                    settings.DASHBOARD_REPORTS_PATH, '%s%.2d_audio_statistics.csv' % (
                        month_before_last.year, month_before_last.month
                    )
                ),
            )

        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '{}audio_statistics.csv'.format(out_prefix)), 'w'))
        for article in articles.iterator():
            # TODO: duration calculation disabled, it raises a UnicodeDecodeError and should be investigated.
            # audio_info = mutagen.File(article.audio.file).info; duration = timedelta(seconds=int(audio_info.length))
            w.writerow([
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
            ])
            if bar:
                bar.next()
        if bar:
            bar.finish()
