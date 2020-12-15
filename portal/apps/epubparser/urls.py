# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.decorators import permission_required
from django.conf.urls.static import static
from django.conf import settings
from .views import FileAddView, ParseView, FileListView, FileChangeView, changeSection

urlpatterns = [
    #url(r'^admin/', include(admin.site.urls)),

    # This is the view that handles the file uploads
    #url(r'^add/?$', FileAddView.as_view(), name='epub-add'),
    url(r'^add/?$',
        permission_required('epubparser.add_epubfile')(FileAddView.as_view()), name='epub-add'),

    # This view lists uploaded files
    url(r'^$',
        permission_required('epubparser.add_epubfile')(FileListView.as_view()), name='epub-home'),

    #This view parse the ebook and create an article
    url(r'^parse-ebook/(?P<pk>\w+)$',
        permission_required('epubparser.add_epubfile')(ParseView.as_view()), name='parse-ebook'),

    url(r'^change/(?P<pk>\w+)$',
        permission_required('epubparser.add_epubfile')(FileChangeView.as_view()), name='epub-change'),

    url(r'^change-section/?$',
        permission_required('epubparser.add_epubfile')('epubparser.views.changeSection'), name='change-section'),



]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)