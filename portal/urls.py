# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import re
from generator.views import contribute
from rest_framework import serializers, viewsets, routers

from django.conf import settings
from django.urls import include, path, re_path
from django.db import ProgrammingError
from django.urls import reverse_lazy
from django.views.generic import TemplateView, RedirectView
from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.static import serve

from core.models import Article, Publication, Category, Section, Journalist, get_current_edition, get_latest_edition
from core.views.edition import edition_detail, edition_list, edition_list_ajax
from core.views.supplement import supplement_list
from core.views.sw import service_worker
from core.views.subscribe import subscribe
from photologue_ladiaria.models import PhotoExtended
from exchange.models import Exchange
from thedaily.models import Subscriber
from comunidad.models import Url, Recommendation
from homev3.views import index
from cartelera.views import vivo


admin.autodiscover()
admin.site.site_header, admin.site.enable_nav_sidebar = "CMS - %s" % settings.SITE_DOMAIN, False


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
            'get_app_photo',  # TODO: fix UnicodeDecodeError
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
        fields = ('recommendation_set',)


class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = ('__str__', 'user_email', 'is_subscriber_any', 'newsletters')


class ExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exchange
        fields = ('date', 'buy', 'sale')


class JournalistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journalist
        fields = ('name',)


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
    filter_fields = ('name',)


class HomeArticleViewSet(viewsets.ModelViewSet):
    try:
        edition = get_current_edition() or get_latest_edition()
    except Exception:
        edition = None
    try:
        pk_list = [a.id for a in edition.top_articles] if edition else []
    except Exception:
        pk_list = []
    clauses = ' '.join(['WHEN id=%s THEN %s' % (pk, i) for i, pk in enumerate(pk_list)])
    ordering = 'CASE %s END' % clauses
    queryset = Article.objects.filter(id__in=pk_list).extra(select={'ordering': ordering}, order_by=('ordering',))
    serializer_class = ArticleSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('headline', 'sections')


class UrlViewSet(viewsets.ModelViewSet):
    permission_classes = ()
    queryset = Url.objects.all()
    serializer_class = UrlSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('url',)


class SubscriberViewSet(viewsets.ModelViewSet):
    queryset = Subscriber.objects.all()
    serializer_class = SubscriberSerializer
    http_method_names = ['get', 'head']
    filter_fields = ('contact_id',)


class DollarExchangeViewSet(viewsets.ModelViewSet):
    queryset = Exchange.objects.filter(currency__slug='dolar').order_by('-date')
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
    path('photologue/', include('photologue.urls', namespace='photologue_photologue')),
    path('epubparser/', include('epubparser.urls')),
    # Admin
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
    # Search
    path('buscar/', include('search.urls')),
    # Service Worker
    re_path(r'^sw\.js$', service_worker, name='serviceworker'),
    path('subscribe/', subscribe, name='subscribe'),
    # Custom redirects
    path('suscribite-por-telefono/', RedirectView.as_view(url='/usuarios/suscribite-por-telefono/')),
    path('suscribite/', RedirectView.as_view(url=reverse_lazy('subscribe_landing'))),
    path('digital/', RedirectView.as_view(url=reverse_lazy('subscribe', args=['DDIGM']))),
    re_path(
        r'^contacto/', RedirectView.as_view(url=getattr(settings, 'CONTACT_REDIRECT_URL', '/')), name="contact-form"
    ),
    # AMP copy iframe
    re_path(r'^copier/', TemplateView.as_view(template_name="core/templates/amp/article/copier.html"), name='copier'),
    # AMP reader ID
    path('amp-readerid/', include('django_amp_readerid.urls')),
]

# Used to add customized url patterns from custom modules
urls_custom_modules = getattr(settings, 'PORTAL_URLS_CUSTOM_MODULES', [])
for item in urls_custom_modules:
    urlpatterns += __import__(item, fromlist=['urlpatterns']).urlpatterns

urlpatterns.extend(
    [
        # Apps
        path('dashboard/', include('dashboard.urls')),
        path('fotos/', include('photologue.urls')),
        path('genera-la-noticia/', contribute, name='generator-contribute'),
        path('memcached/', include('memcached.urls')),
        re_path(r'^robots.txt', include('robots.urls')),
        path('shout/', include('shoutbox.urls')),
        path('activity/', include('actstream.urls')),
        path('favit/', include('favit.urls')),

        # Vivo
        path('vivo/', vivo, name="cartelera-vivo"),
        path('vivo/archivo/<int:archived_event_id>/', vivo, name="cartelera-archive"),

        # Other apps
        path('comunidad/', include('comunidad.urls')),
        path("cartelera/", include("cartelera.urls")),
        path('tagging_autocomplete_tagit/', include('tagging_autocomplete_tagit.urls')),
        path('adzone/', include('adzone.urls')),
        path('avatar/', include('avatar.urls')),
        path('martor/', include('martor.urls')),

        # Rest Framework API
        path('api/', include(router.urls)),
        path('api/auth/', include('rest_framework.urls', namespace='rest_framework')),

        # Editions
        path('ediciones/', edition_list, name='edition_list'),
        re_path(r'^ediciones/(?P<year>\d{4})/(?P<month>\d{1,2})/$', edition_list_ajax, name='edition_list_ajax'),
        path('edicion/', include('core.urls.edition')),
        re_path(
            r'^(?P<publication_slug>[\w-]+)/edicion/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
            edition_detail,
            name='edition_detail',
        ),

        # Most read
        path('masleidos/', include('core.urls.masleidos')),

        # supplements
        re_path(r'^suplementos/', supplement_list, name='supplement_list'),
        path('suplemento/', include('core.urls.supplement')),

        # Homes: domain_slug can be a publication slug or an area (core.Category) slug
        path('', index, name='home'),
        re_path(r'^(?P<domain_slug>[\w-]+)/$', index, name='home'),

        # Article detail pages: domain_slug can be a publication slug or an area slug
        path('articulo/', include('core.urls.article')),
        re_path(r'^(?P<domain_slug>[\w-]+)/articulo/', include('core.urls.article')),

        # Artcles (other pages that show articles)
        path('articulos/', include('core.urls.article.type')),  # Articles by type
        path('seccion/', include('core.urls.section')),  # Articles by section
        path('tags/', include('core.urls.tag')),

        # Other pages (TODO: check and organize better)
        re_path(r'^(?P<journalist_job>(periodista|columnista))/', include('core.urls.journalist')),
        path('area/', include('core.urls.category')),
        path('bn/', include('core.urls.breaking_news_module')),
    ]
)

# Used to customize "/custom_email/*" urls using patterns from a custom app
custom_email_urls_module = getattr(settings, 'CUSTOM_EMAIL_URLS_MODULE', None)
if custom_email_urls_module:
    urlpatterns.append(path('custom_email/', include(custom_email_urls_module)))

urlpatterns.extend(
    [
        path('debug/', include('core.urls.debug')),
        # Usuarios
        path('usuarios/', include('thedaily.urls')),
        # notification (TODO: move to thedaily.urls)
        path('usuarios/alertas/', include('notification.urls')),
        # TODO: verify if this repeated path (?) makes sense
        path('', include('sitemaps.urls')),
        path('', include('social_django.urls', namespace='social')),
    ]
)

# Shorturl machinery (enabled by default) (TODO: check if working)
if getattr(settings, 'ENABLE_SHORTURLS', True):
    urlpatterns += [path('', include('shorturls.urls')), path('short/', include('short.urls'))]

# Syndication framework, only available when a Site object can be defined
try:
    Site.objects.get_current()
except (ProgrammingError, Site.DoesNotExist):
    pass
else:
    from feeds import ArticlesByJournalist, LatestArticlesByCategory, LatestEditions, LatestSupplements, LatestArticles
    urlpatterns += [
        path('feeds/articulos/', LatestArticles(), name='ultimos-articulos-rss'),
        path('feeds/ediciones/', LatestEditions()),
        re_path(r'^feeds/periodista/(?P<journalist_slug>[\w-]+)/$', ArticlesByJournalist()),
        re_path(r'^feeds/seccion/(?P<section_slug>[\w-]+)/$', LatestArticlesByCategory()),
        path('feeds/suplementos/', LatestSupplements()),
    ]

if 'debug_toolbar' in settings.INSTALLED_APPS:
    # WARNING: more settings are needed to use django-debug-toolbar<1.11.1
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns.append(re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}))
    # TODO: explain this old commented code
    # urlpatterns += patterns(
    #    '', (r'^media/(?P<path>.*)$', {'document_root': settings.MEDIA_ROOT, 'show_indexes': settings.DEBUG})
    # )
else:
    urlpatterns.append(re_path(r'^.*.css$', TemplateView.as_view(template_name='devnull.html')))
