# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.feedgenerator import DefaultFeed, Rss201rev2Feed
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404

from libs.utils import get_site_name
from core.models import Article, get_current_edition, get_current_feeds, Journalist, Section, Supplement, Edition
from core.templatetags.ldml import ldmarkup, cleanhtml


# IPTC Media Topic codes: https://cv.iptc.org/newscodes/mediatopic/
SECTION_IPTC_MAP = {
    # Politics (11000000)
    'politica-nacional': '11000000', 'politica-internacional': '11000000',
    'gobierno-nacional': '11000000', 'frente-amplio': '11000000',
    'partido-nacional': '11000000', 'partido-colorado': '11000000',
    'cabildo-abierto': '11000000', 'partidos-politicos': '11000000',
    'coalicion': '11000000', 'parlamento': '11000000',
    'gobiernos-departamentales': '11000000', 'plebiscitos': '11000000',
    'transicion-2020': '11000000', 'editorial': '11000000',
    'elecciones-departamentales-2020': '11000000',
    # Economy (04000000)
    'economia': '04000000', 'actividad-economica': '04000000',
    'comercio-y-sector-externo': '04000000', 'indicadores-economicos': '04000000',
    'precios': '04000000', 'sector-publico': '04000000',
    'economia-social': '04000000', 'concentracion-de-la-riqueza-y-endeudamiento': '04000000',
    # Sport (15000000)
    'deporte': '15000000', 'futbol': '15000000', 'futbol-femenino': '15000000',
    'basquetbol': '15000000', 'ciclismo': '15000000', 'atletismo': '15000000',
    'tenis': '15000000', 'rugby': '15000000', 'otros-deportes': '15000000',
    'plaza-de-deportes': '15000000', 'juegos-olimpicos-de-tokio': '15000000',
    # Arts, entertainment and media (01000000)
    'cultura': '01000000', 'arte': '01000000', 'musica': '01000000',
    'teatro': '01000000', 'cine-tv-streaming': '01000000', 'letras': '01000000',
    'libros-novedades': '01000000', 'libros-recomendaciones-de-la-diaria': '01000000',
    'libros-recomendaciones-de-biblioteca-pais': '01000000',
    'libros-recomendaciones-de-la-comunidad': '01000000', 'libros-editores': '01000000',
    'libros-entrevistas': '01000000', 'libros-resenas': '01000000',
    'fotografia': '01000000', 'medios': '01000000', 'humor': '01000000',
    'videojuegos': '01000000', 'carnaval-2020': '01000000',
    'murgas': '01000000', 'parodistas': '01000000', 'conjuntos': '01000000',
    'otros-conjuntos': '01000000', 'sociedad-de-negros-y-lubolos': '01000000',
    # Science and technology (13000000)
    'ciencia': '13000000', 'investigacion-cientifica': '13000000',
    'comunidad-cientifica': '13000000', 'politica-de-ciencia': '13000000',
    'perfiles-cientificos': '13000000', 'ciencia-y-cultura': '13000000',
    'tecnologia': '13000000', 'fabrica-de-ideas': '13000000',
    # Health (07000000)
    'politicas-de-salud': '07000000', 'atencion-de-salud': '07000000',
    'calidad-de-vida': '07000000', 'afecciones-y-tratamientos': '07000000',
    'investigacion-en-salud': '07000000', 'discapacidad': '07000000',
    'coronavirus': '07000000', 'coronavirus-en-uruguay': '07000000',
    'coronavirus-en-el-mundo': '07000000', 'ciencia-y-coronavirus': '07000000',
    # Education (05000000)
    'educacion': '05000000', 'sistema-educativo': '05000000',
    'practicas-educativas': '05000000', 'educacion-primaria': '05000000',
    'educacion-media': '05000000', 'educacion-terciaria': '05000000',
    # Environment (06000000)
    'ambiente-y-produccion': '06000000', 'crisis-climatica': '06000000',
    'debates-ambientales': '06000000', 'ecosistemas': '06000000',
    'flora-y-fauna': '06000000', 'agua': '06000000',
    'economia-y-ambiente': '06000000', 'educacion-y-ambiente': '06000000',
    'pesca-y-playas': '06000000', 'cuencas-y-acuiferos': '06000000',
    # Crime, law and justice (02000000)
    'seguridad': '02000000', 'crimen-organizado': '02000000',
    'delitos': '02000000', 'fuerzas-de-seguridad': '02000000',
    'sistema-judicial': '02000000', 'procesos-judiciales': '02000000',
    'carceles': '02000000', 'victimas': '02000000',
    # Labour (09000000)
    'trabajo': '09000000', 'conflictos-laborales': '09000000',
    'empleo-y-produccion': '09000000', 'futuro-del-trabajo': '09000000',
    'trabajo-mundo': '09000000',
    # Social issues (14000000)
    'sociedad': '14000000', 'derechos-humanos': '14000000',
    'derechos-sexuales-y-reproductivos': '14000000', 'ninez-y-adolescencia': '14000000',
    'vivienda-y-acceso-a-la-tierra': '14000000', 'desigualdad-y-pobreza': '14000000',
    'politicas-de-genero': '14000000', 'movimientos-feministas': '14000000',
    'violencias': '14000000', 'lgbti': '14000000',
    'exclusion-social-y-resistencia': '14000000',
}
IPTC_DEFAULT = '11000000'  # Politics as fallback for general news


class GoogleNewsAIFeedGenerator(Rss201rev2Feed):
    """Custom RSS feed generator with namespaces required by Google News AI pilot."""

    def rss_attributes(self):
        attrs = super().rss_attributes()
        attrs['xmlns:content'] = 'http://purl.org/rss/1.0/modules/content/'
        attrs['xmlns:dcterms'] = 'http://purl.org/dc/terms/'
        attrs['xmlns:licensed_news'] = 'https://www.google.com/schemas/rss-licensed-news/'
        attrs['xmlns:media'] = 'http://search.yahoo.com/mrss/'
        return attrs

    def add_item_elements(self, handler, item):
        super().add_item_elements(handler, item)
        if item.get('content_encoded'):
            handler.addQuickElement('content:encoded', item['content_encoded'])
        if item.get('dcterms_creator'):
            handler.addQuickElement('dcterms:creator', item['dcterms_creator'])
        if item.get('dcterms_modified'):
            handler.addQuickElement('dcterms:modified', item['dcterms_modified'])
        if item.get('media_content_url'):
            handler.addQuickElement('media:content', '', {'url': item['media_content_url'], 'medium': 'image'})
            if item.get('media_title'):
                handler.addQuickElement('media:title', item['media_title'])


class GoogleNewsAIFeed(Feed):
    feed_type = GoogleNewsAIFeedGenerator
    title = get_site_name()
    link = '/'
    description = u'Google News AI licensed feed for %s.' % get_site_name()
    item_guid_is_permalink = True

    def items(self):
        return get_current_feeds()

    def item_title(self, item):
        return cleanhtml(ldmarkup(item.headline))

    def item_description(self, item):
        return cleanhtml(ldmarkup(item.deck)) if item.deck else cleanhtml(ldmarkup(item.headline))

    def item_pubdate(self, item):
        return item.date_published

    def item_categories(self, item):
        sections = item.sections.values_list('slug', flat=True)
        codes = list({SECTION_IPTC_MAP.get(s, IPTC_DEFAULT) for s in sections})
        return codes if codes else [IPTC_DEFAULT]

    def item_extra_kwargs(self, item):
        authors = item.get_authors()
        creator = ' and '.join(a.name for a in authors) if authors else ''
        media_url = ''
        media_title = ''
        if item.photo and item.photo.image:
            media_url = '%s://%s%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN, item.photo.image.url)
            media_title = item.photo.title if hasattr(item.photo, 'title') else ''
        return {
            'content_encoded': ldmarkup(item.body),
            'dcterms_creator': creator,
            'dcterms_modified': item.last_modified.isoformat(),
            'media_content_url': media_url,
            'media_title': media_title,
        }


site_name = get_site_name()


# TODO: unicode improvements

class LatestArticles(Feed):
    feed_type = DefaultFeed
    title = site_name
    link = '/'
    description = u'Artículos de la publicación periodística %s.' % site_name
    item_guid_is_permalink = False

    def item_guid(self, item):
        return u'%s.%d' % (settings.SITE_DOMAIN, item.id)

    def items(self):
        return get_current_feeds()

    def item_title(self, item):
        return cleanhtml(ldmarkup(item.headline))

    def item_description(self, item):
        deck = "<h2>%s</h2><br/>" % ldmarkup(item.deck) if item.deck else ""
        return "%s" % deck + ldmarkup(item.body[:400] + "...") + '<a href="%s://%s%s">Continuar leyendo...</a>' % (
            settings.URL_SCHEME, settings.SITE_DOMAIN, item.get_absolute_url()
        )

    def item_pubdate(self, item):
        return item.date_published

    def item_author_name(self, item):
        authors = item.get_authors()
        return authors[0] if authors else ""

    def item_categories(self, item):
        return [item.get_sections()]


class LatestArticlesByCategory(Feed):
    link = '/'

    def get_object(self, *args, **kwargs):
        return get_object_or_404(Section, slug=kwargs.get('section_slug'))

    def title(self, obj):
        return u'%s - %s' % (site_name, obj.name)

    def link(self, obj):  # noqa
        # TODO: redefined (fix)
        return obj.get_absolute_url()

    def description(self, obj):
        return u'Artículos de la sección "%s" de %s.' % (obj.name, site_name)

    def items(self, obj):
        return obj.latest_articles()


class LatestEditions(Feed):
    title = u'%s - Ediciones' % site_name
    link = '/'
    description = u'Ediciones de la publicación periodística %s.' % site_name

    def items(self):
        edition = get_current_edition()
        return Edition.objects.filter(id__lte=edition.id)[:10]


class LatestSupplements(Feed):
    title = u'%s - Suplementos' % site_name
    link = '/'
    description = u'Suplementos de la publicación periodística %s.' % site_name

    def items(self):
        edition = get_current_edition()
        return Supplement.objects.filter(edition__id__lte=edition.id, public=True)[:10]


class ArticlesByJournalist(Feed):
    link = '/'

    def title(self, obj):
        return u'%s - %s' % (site_name, obj.name)

    def get_object(self, *args, **kwargs):
        return get_object_or_404(Journalist, slug=kwargs.get('journalist_slug'))

    def description(self, obj):
        return u'Artículos escritos por %s' % obj.name

    def items(self, obj):
        return Article.published.filter(byline=obj)[:10]

    def item_link(self, obj):
        return obj.get_absolute_url()

    def item_pubdate(self, obj):
        return obj.date_published
