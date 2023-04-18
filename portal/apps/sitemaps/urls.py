from __future__ import unicode_literals
from django.urls import re_path
from .views import index, sitemap

urlpatterns = [
    re_path(r'^sitemap.xml$', index, {'sitemap_url_name': 'sitemap'}),
    re_path(r'^sitemap-(?P<section>.+)\.xml$', sitemap, name='sitemap'),
]

