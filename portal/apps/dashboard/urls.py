# -*- coding: utf-8 -*-
from django.conf.urls import url

from views import index, export_csv, load_table, audio_statistics_api, audio_statistics_api_amp


tables = (
    'activity',
    'activity_only_digital',
    'articles',
    'sections',
    'subscribers',
    'subscribers_sections',
    'audio_statistics',
    'categories',
    'article_views',
    'audio_statistics'
)

formatted_tables = "|".join(table_name for table_name in tables)

urlpatterns = [
    url(r'^$', index, name="index"),
    url(
        r'^export/(?P<table_id>{})/$'.format(formatted_tables),
        export_csv,
        name="export_csv",
    ),
    url(
        r'^table/(?P<table_id>{})/$'.format(formatted_tables),
        load_table,
        name="load_table",
    ),
    url(r'^audio_statistics_api/$', audio_statistics_api, name="audio_statistics_api"),
    url(r'^audio_statistics_api_amp/$', audio_statistics_api_amp, name="audio_statistics_api_amp"),
]
