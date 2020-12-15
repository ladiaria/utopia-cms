# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.views.generic import TemplateView, RedirectView

from elegi_informarte.views import suscripcion, attribution


urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(
        template_name='elegi_informarte/templates/index.html'),
        name='elegi-informarte'),
    url(r'^colaborar/$', attribution, name='elegi-informarte-colaborar'),
    url(r'^change-amount/$', RedirectView.as_view(
        url='/elegi-informarte/colaborar/#form'),
        name='elegi-informarte-change-amount'),
    url(r'^suscripcion/$', suscripcion, name='elegi-informarte-suscripcion'),
    url(r'^preguntas/$', TemplateView.as_view(
        template_name='elegi_informarte/templates/preguntas.html'),
        name='elegi-informarte-preguntas')
)
