from django.conf.urls import url
from .views import index, sitemap

urlpatterns = [
    url(r'^sitemap.xml$', index, {'sitemap_url_name': 'sitemap'}),
    url(r'^sitemap-(?P<section>.+)\.xml$', sitemap, name='sitemap'),
]

