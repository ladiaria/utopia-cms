# -*- coding: utf-8 -*-
from django.conf.urls import url
from django.views.generic import TemplateView

from core.views.edition import edition_detail, edition_download, rawpic_cover


urlpatterns = [
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', edition_detail, name='edition_detail'),
    url(
        r'^descargar/(?P<publication_slug>\w+)/(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})/(?P<filename>[-\w\.]+)$',
        edition_download,
        name='edition_download',
    ),
    url(r'^descargar/error/$', edition_download, name='edition_download_error'),
    url(
        r'^descargar/link-invalido/$',
        TemplateView.as_view(template_name='core/templates/edition/download_invalid.html'),
        name='edition_download_invalid',
    ),
    url(
        r'^descargar/suscribite/$',
        TemplateView.as_view(template_name='core/templates/edition/download_subscribe.html'),
        name='edition_download_subscribe',
    ),
    url(
        r'^descargar/email/$',
        TemplateView.as_view(template_name='core/templates/edition/download_email_sent.html'),
        name='edition_download_email_sent',
    ),
    url(r'^descargar/suscribite/$', edition_download, name='edition_download_subscribe'),
    url(r'^imagenportada/$', rawpic_cover, name='rawpic_cover'),
]
