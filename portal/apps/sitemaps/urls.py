from django.urls import re_path
from .views import index, sitemap

urlpatterns = [
    re_path(r'^sitemap.xml$', index, {'sitemap_url_name': 'sitemap'}),
    re_path(r'^sitemap-news_48hs.xml$',
            sitemap,
            {'section': 'news_48hs', 'template_name': 'sitemaps/templates/sitemap_news.xml'},
            name='sitemap_news_48hs'
            ),
    re_path(r'^sitemap-(?P<section>.+)\.xml$', sitemap, name='sitemap'),
]
