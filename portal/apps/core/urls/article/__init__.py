# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.urls import path, re_path
from django.views.generic import TemplateView

from core.views.article import article_detail_walled, article_detail_free, send_by_email, article_detail_ipfs


urlpatterns = [
    path(
        'reportar/',
        TemplateView.as_view(template_name='core/templates/article/reported.html'),
        name='article_report_sent',
    ),
    path("enviar/", send_by_email, name="send_by_email"),
    re_path(r"^ipfs/(?P<article_id>\d+)/$", article_detail_ipfs, name="ipfs-article-detail"),
    re_path(
        r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<slug>[\w-]+)/$',
        article_detail_walled if settings.SIGNUPWALL_ENABLED else article_detail_free,
        name='article_detail',
    ),
]
