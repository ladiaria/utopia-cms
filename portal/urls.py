# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import re
from generator.views import contribute
from rest_framework import serializers, viewsets, routers

from django.conf import settings
from django.conf.urls import url, include
from django.db import ProgrammingError
from django.core.urlresolvers import reverse_lazy
from django.views.generic import TemplateView, RedirectView
from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.static import serve

from core.models import Article, Publication, Category, Section, Journalist, get_current_edition, get_latest_edition
from core.views.edition import edition_detail, edition_list, edition_list_ajax
from core.views.supplement import supplement_list
from core.views.sw import service_worker
from photologue_ladiaria.models import PhotoExtended
from exchange.models import Exchange
from thedaily.models import Subscriber
from thedaily.views import fav_add_or_remove
from comunidad.models import Url, Recommendation
from homev3.views import index
from cartelera.views import vivo


admin.autodiscover()


# Serializers define the API representation.
class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoExtended
        fields = ('image', )


class ArticleSerializer(serializers.ModelSerializer):
    get_app_photo = PhotoSerializer()

    class Meta:
        model = Article
        fields = (
            'id',
            'type',
            'date_published',
            'sections',
            'headline',
            'keywords',
            'slug',
            'deck',
            'lead',
            'get_app_body',
            'get_app_photo',
            'get_absolute_url',
        )
        depth = 1


class PublicationSerializer(serializers.ModelSerializer):
    latest_articles = ArticleSerializer(many=True)

    class Meta:
        model = Publication
        fields = ('name', 'slug', 'latest_articles')
        depth = 1


class CategorySerializer(serializers.ModelSerializer):
    latest_articles = ArticleSerializer(many=True)

    class Meta:
        model = Category
        fields = ('name', 'slug', 'latest_articles')
        depth = 1


class SectionSerializer(serializers.ModelSerializer):
    latest_articles = ArticleSerializer(many=True)

    class Meta:
        model = Section
        fields = ('name', 'slug', 'latest_articles')
        depth = 1


class RecommendationSerializer(serializers.ModelSerializer):
    article = ArticleSerializer()

    class Meta:
        model = Recommendation
        fields = ('comment', 'article')


class UrlSerializer(serializers.ModelSerializer):
    recommendation_set = RecommendationSerializer(many=True)

    class Meta:
        model = Url
        fields = ('recommendation_set', )


class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = ('user_email', 'newsletters')


class ExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exchange
        fields = ('date', 'buy', 'sale')


class JournalistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journalist
        fields = ('name', )


# ViewSets define the view behavior.
class PhotoViewSet(viewsets.ModelViewSet):
    queryset = PhotoExtended.objects.all()
    serializer_class = PhotoSerializer
    http_method_names = ['get', 'head']


class PublicationViewSet(viewsets.ModelViewSet):
    queryset = Publication.objects.all()
    serializer_class = PublicationSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('name', 'slug')


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    http_method_names = ['get', 'head']
    filter_fields = ('name', 'slug')


RE_SLUG_APP_COMPAT = re.compile(r'([\w-]+)-ladiaria$')


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('name', 'slug')

    def filter_queryset(self, queryset):
        """
        Mobile APP compatibility (slugs ending with "-ladiaria")
        https://stackoverflow.com/a/39849686
        WARNING: filtering by name will be ignored here
        """
        slug = self.request.query_params.get('slug', None)
        if slug is not None:
            compat_slug_match = re.match(RE_SLUG_APP_COMPAT, slug)
            if compat_slug_match:
                slug = compat_slug_match.groups()[0]
            queryset = queryset.filter(slug=slug)
        return queryset


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.published.all()
    serializer_class = ArticleSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('headline', 'sections')


class JournalistViewSet(viewsets.ModelViewSet):
    queryset = Journalist.objects.all()
    serializer_class = JournalistSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('name', )


class HomeArticleViewSet(viewsets.ModelViewSet):
    try:
        edition = get_current_edition() or get_latest_edition()
    except Exception:
        edition = None
    pk_list = [a.id for a in edition.top_articles] if edition else []
    clauses = ' '.join(['WHEN id=%s THEN %s' % (pk, i) for i, pk in enumerate(pk_list)])
    ordering = 'CASE %s END' % clauses
    queryset = Article.objects.filter(id__in=pk_list).extra(select={'ordering': ordering}, order_by=('ordering', ))
    serializer_class = ArticleSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('headline', 'sections')


class UrlViewSet(viewsets.ModelViewSet):
    permission_classes = ()
    queryset = Url.objects.all()
    serializer_class = UrlSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('url', )


class SubscriberViewSet(viewsets.ModelViewSet):
    queryset = Subscriber.objects.all()
    serializer_class = SubscriberSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('contact_id', )


class DollarExchangeViewSet(viewsets.ModelViewSet):
    queryset = Exchange.objects.filter(
        currency__slug='dolar').order_by('-date')
    serializer_class = ExchangeSerializer
    http_method_names = ['get', 'head']


# Routers provide a way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'photos', PhotoViewSet)
router.register(r'publications', PublicationViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'articles', ArticleViewSet)
router.register(r'home', HomeArticleViewSet)
router.register(r'journalists', JournalistViewSet)
router.register(r'urls', UrlViewSet)
router.register(r'subscribers', SubscriberViewSet)
router.register(r'dollar_exchange', DollarExchangeViewSet)

urlpatterns = [
    url(r'^photologue/', include('photologue.urls', namespace='photologue')),
    url(r'^epubparser/', include('epubparser.urls')),

    # Admin
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    # Search
    url(r'^buscar/', include('search.urls')),

    # Service Worker
    url(r'^sw\.js$', service_worker, name='serviceworker'),

    # Custom redirects
    url(r'^suscribite-por-telefono/$', RedirectView.as_view(url='/usuarios/suscribite-por-telefono/')),
    url(r'^suscribite/$', RedirectView.as_view(url=reverse_lazy('subscribe_landing'))),
    url(r'^digital/$', RedirectView.as_view(url=reverse_lazy('subscribe', args=['DDIGM']))),
    url(r'^contacto/', RedirectView.as_view(url=getattr(settings, 'CONTACT_REDIRECT_URL', '/')), name="contact-form"),

    # AMP copy iframe
    url(r'^copier/', TemplateView.as_view(template_name="amp/core/templates/article/copier.html"), name='copier'),
]

# Used to add customized url patterns from a custom app
urls_custom_module = getattr(settings, 'PORTAL_URLS_CUSTOM_MODULE', None)
if urls_custom_module:
    urlpatterns += __import__(urls_custom_module, fromlist=['urlpatterns']).urlpatterns

urlpatterns.extend([
    # Apps
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^fotos/', include('photologue.urls')),
    url(r'^genera-la-noticia/$', contribute, name='generator-contribute'),
    url(r'^memcached/', include('memcached.urls')),
    url(r'^robots.txt', include('robots.urls')),
    url(r'^shout/', include('shoutbox.urls')),
    url(r'^activity/', include('actstream.urls')),

    # favit add-or-remove wrapper (TODO: favit should be replaced asap with a more compatible Django1.11+ app)
    url(r'^favit/add-or-remove$', fav_add_or_remove),

    # Vivo
    url(r'^vivo/$', vivo, name="cartelera-vivo"),
    url(r'^vivo/archivo/(?P<archived_event_id>\d+)/$', vivo, name="cartelera-archive"),

    # Other apps
    url(r'^comunidad/', include('comunidad.urls')),
    url(r"^cartelera/", include("cartelera.urls")),
    url(r'^tagging_autocomplete_tagit/', include('tagging_autocomplete_tagit.urls')),
    url(r'^adzone/', include('adzone.urls')),
    url(r'^avatar/', include('avatar.urls')),
    url(r'^markdown/', include('django_markdown.urls')),

    # Rest Framework API
    url(r'^api/', include(router.urls)),
    url(r'^api/auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Editions
    url(r'^ediciones/$', edition_list, name='edition_list'),
    url(r'^ediciones/(?P<year>\d{4})/(?P<month>\d{1,2})/$', edition_list_ajax, name='edition_list_ajax'),
    url(r'^edicion/', include('core.urls.edition')),
    url(
        r'^(?P<publication_slug>[\w-]+)/edicion/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        edition_detail,
        name='edition_detail',
    ),

    # Most read
    url(r'^masleidos/', include('core.urls.masleidos')),

    # supplements
    url(r'^suplementos/', supplement_list, name='supplement_list'),
    url(r'^suplemento/', include('core.urls.supplement')),

    # Homes: domain_slug can be a publication slug or an area (core.Category) slug
    url(r'^$', index, name='home'),
    url(r'^(?P<domain_slug>[\w-]+)/$', index, name='home'),

    # Article detail pages: domain_slug can be a publication slug or an area slug
    url(r'^articulo/', include('core.urls.article')),
    url(r'^(?P<domain_slug>[\w-]+)/articulo/', include('core.urls.article')),

    # Artcles (other pages that show articles)
    url(r'^articulos/', include('core.urls.article.type')),  # Articles by type
    url(r'^seccion/', include('core.urls.section')),  # Articles by section
    url(r'^tags/', include('core.urls.tag')),

    # Other pages (TODO: check and organize better)
    url(r'^(?P<journalist_job>(periodista|columnista))/', include('core.urls.journalist')),
    url(r'^area/', include('core.urls.category')),
    url(r'^bn/', include('core.urls.breaking_news_module'))])

# Used to customize "/custom_email/*" urls using patterns from a custom app
custom_email_urls_module = getattr(settings, 'CUSTOM_EMAIL_URLS_MODULE', None)
if custom_email_urls_module:
    urlpatterns.extend([url(r'^custom_email/', include(custom_email_urls_module))])

urlpatterns.extend([
    url(r'^debug/', include('core.urls.debug')),

    # Usuarios
    url(r'^usuarios/', include('thedaily.urls')),

    # notification (TODO: move to thedaily.urls)
    url(r'^usuarios/alertas/', include('notification.urls')),

    # TODO: verify if this repeated path (?) makes sense
    url('', include('sitemaps.urls')),

    url('', include('social_django.urls', namespace='social')),
])

# Shorturl machinery (enabled by default) (TODO: check if working)
if getattr(settings, 'ENABLE_SHORTURLS', True):
    urlpatterns += [
        url(r'^', include('shorturls.urls')),
        url(r'^short/', include('short.urls')),
    ]

# Syndication framework, only available when a Site object can be defined
try:
    Site.objects.get_current()
except (ProgrammingError, Site.DoesNotExist):
    pass
else:
    from feeds import (
        ArticlesByJournalist, LatestArticlesByCategory, LatestEditions, LatestSupplements, LatestArticles
    )
    urlpatterns += [
        url(r'^feeds/articulos/$', LatestArticles(), name='ultimos-articulos-rss'),
        url(r'^feeds/ediciones/$', LatestEditions()),
        url(r'^feeds/periodista/(?P<journalist_slug>[\w-]+)/$', ArticlesByJournalist()),
        url(r'^feeds/seccion/(?P<section_slug>[\w-]+)/$', LatestArticlesByCategory()),
        url(r'^feeds/suplementos/$', LatestSupplements()),
    ]

if 'debug_toolbar' in settings.INSTALLED_APPS:
    # WARNING: more settings are needed to use django-debug-toolbar<1.11.1
    import debug_toolbar
    urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls))]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]
# TODO: explain this
#    urlpatterns += patterns('',
#            (r'^media/(?P<path>.*)$',
#            {'document_root': settings.MEDIA_ROOT,
#            'show_indexes': settings.DEBUG}),)
else:
    urlpatterns += [
        url(r'^.*.css$', TemplateView.as_view(template_name='devnull.html')),
    ]
