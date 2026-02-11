# -*- coding: utf-8 -*-

from django.urls import path, re_path

from .views import index, export_csv, load_table, audio_statistics_api, audio_statistics_api_amp, nl_open


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
    'article_views_subscribers_only',
    'audio_statistics',
)

formatted_tables = "|".join(table_name for table_name in tables)

urlpatterns = [
    path('', index, name="index"),
    re_path(r'^export/(?P<table_id>{})/$'.format(formatted_tables), export_csv, name="export_csv"),
    re_path(r'^table/(?P<table_id>{})/$'.format(formatted_tables), load_table, name="load_table"),
    path('audio_statistics_api/', audio_statistics_api, name="audio_statistics_api"),
    path('audio_statistics_api_amp/', audio_statistics_api_amp, name="audio_statistics_api_amp"),
    re_path(r"nl_open/(?P<nl_delivery_id>\d{1,})/(?P<nl_delivery_segment>user|subscriber)/", nl_open, name="nl_open"),
]
