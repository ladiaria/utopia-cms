# -*- coding: utf-8 -*-
from core.views.section import (
    section_detail, set_pdf_for_route, latest_article)

from django.conf.urls.defaults import patterns, url


urlpatterns = patterns(
    '',
    url(r'^(?P<section_slug>[\w-]+)/$', section_detail, name='section_detail'),
    url(r'^(?P<section_slug>[\w-]+)/articulo_mas_reciente/$', latest_article, name='section-latest-article'),
    url(r'^(?P<section_slug>[\w-]+)/(?P<tag>[\w-]+)/$', section_detail, name='section_detail'),
    url(r'^(?P<section_slug>[\w-]+)/(?P<year>\d{4})/(?P<month>\d{1,2})/'
        r'(?P<day>\d{1,2})/$', section_detail, name='section_detail'),
    url(r'enviar_pdf/rutas/(?P<ruta>\d+|listar)/$', set_pdf_for_route),
)
