# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

from views import index, export_csv, load_table, audio_statistics_api, audio_statistics_dashboard


urlpatterns = patterns(
    '',
    url(r'^$', index, name="index"),
    url(
        r'^export/(?P<table_id>activity|activity_only_digital|articles|sections|subscribers|subscribers_sections)/$',
        export_csv, name="export_csv"),
    url(
        r'^table/(?P<table_id>activity|activity_only_digital|articles|sections|subscribers|subscribers_sections)/$',
        load_table, name="load_table"),
    url(r'^audio_statistics_api/$', audio_statistics_api, name="audio_statistics_api"),
    url(r'^audio_statistics/$', audio_statistics_dashboard, name="audio_statistics"),
)
