# -*- coding: utf-8 -*-
from django.urls import path, re_path
from django.views.generic import TemplateView

from core.views.edition import edition_detail, edition_download, rawpic_cover


urlpatterns = [
    re_path(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', edition_detail, name='edition_detail'),
    re_path(
        r'^descargar/(?P<publication_slug>\w+)/(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})/(?P<filename>[-\w\.]+)$',
        edition_download,
        name='edition_download',
    ),
    path('descargar/error/', edition_download, name='edition_download_error'),
    path(
        'descargar/link-invalido/',
        TemplateView.as_view(template_name='core/templates/edition/download_invalid.html'),
        name='edition_download_invalid',
    ),
    path(
        'descargar/suscribite/',
        TemplateView.as_view(template_name='core/templates/edition/download_subscribe.html'),
        name='edition_download_subscribe',
    ),
    path(
        'descargar/email/',
        TemplateView.as_view(template_name='core/templates/edition/download_email_sent.html'),
        name='edition_download_email_sent',
    ),
    path('descargar/suscribite/', edition_download, name='edition_download_subscribe'),
    path('imagenportada/', rawpic_cover, name='rawpic_cover'),
]
