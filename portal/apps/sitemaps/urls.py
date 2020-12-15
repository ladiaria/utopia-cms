
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    'sitemaps.views',
    url(r'^sitemap.xml$', 'index', {'sitemap_url_name': 'sitemaps.views.sitemap'}),
    url(r'^sitemap-(?P<section>.+)\.xml$', 'sitemap'))
