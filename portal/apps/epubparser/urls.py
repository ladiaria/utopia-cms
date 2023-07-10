# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path, re_path
from django.contrib.auth.decorators import permission_required
from django.conf.urls.static import static
from django.conf import settings

from .views import FileAddView, ParseView, FileListView, FileChangeView, changeSection


urlpatterns = [
    # This is the view that handles the file uploads
    re_path(r'^add/?$', permission_required('epubparser.add_epubfile')(FileAddView.as_view()), name='epub-add'),

    # This view lists uploaded files
    path('', permission_required('epubparser.add_epubfile')(FileListView.as_view()), name='epub-home'),

    # This view parse the ebook and create an article
    re_path(
        r'^parse-ebook/(?P<pk>\w+)$',
        permission_required('epubparser.add_epubfile')(ParseView.as_view()),
        name='parse-ebook',
    ),

    re_path(
        r'^change/(?P<pk>\w+)$',
        permission_required('epubparser.add_epubfile')(FileChangeView.as_view()),
        name='epub-change',
    ),

    re_path(
        r'^change-section/?$',
        permission_required('epubparser.add_epubfile')('epubparser.views.changeSection'),
        name='change-section',
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
