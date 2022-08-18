# -*- coding: utf-8 -*-
from tqdm import tqdm
from dateutil.relativedelta import relativedelta
from os.path import join
from csv import writer
from datetime import date

from django.conf import settings

from core.models import Article

# Creates monthly files that are going to be displayed in audio_statistics part of the dashboard,
# for all articles published after date_i, iterating every one month.

date_i = date(2020, 12, 1)

while date_i < date.today():
    date_until = date_i + relativedelta(months=1)
    print("Starting populating audio from articles from {} to {}".format(date_i, date_until))
    articles = Article.published.filter(
        audio__isnull=False,
        date_published__gte=date_i,
        date_published__lte=date_until).select_related('main_section__section', 'audio').distinct()
    w = writer(
        open(join(settings.DASHBOARD_REPORTS_PATH, '%s%.2d_audio_statistics.csv' % (date_i.year, date_i.month)), 'w'))
    for article in tqdm(articles):
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
    date_i = date_i + relativedelta(months=1)
