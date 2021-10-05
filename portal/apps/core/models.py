# -*- coding: utf-8 -*-
import os
import tempfile
import operator
from copy import copy
from datetime import date, datetime, timedelta
from collections import OrderedDict
from sorl.thumbnail import get_thumbnail
from PIL import Image
import readtime

from django.conf import settings
from django.core import urlresolvers
from django.http import HttpResponse, Http404
from django.contrib.auth.models import User
from django.contrib.sitemaps import ping_google
from django.db.models import (
    Manager,
    Model,
    CharField,
    TextField,
    DateField,
    DateTimeField,
    PositiveIntegerField,
    BooleanField,
    OneToOneField,
    ForeignKey,
    SlugField,
    FileField,
    ImageField,
    DecimalField,
    EmailField,
    ManyToManyField,
    PositiveSmallIntegerField,
    URLField,
    permalink,
    SET_NULL,
)
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.utils import timezone

from managers import PublishedArticleManager
from utils import get_pdf_pdf_upload_to, get_pdf_cover_upload_to

from apps import blacklisted
from core.utils import CT, smart_quotes
from core.templatetags.ldml import ldmarkup, cleanhtml
from photologue_ladiaria.models import PhotoExtended
from photologue.models import Gallery, Photo
from audiologue.models import Audio
from tagging.fields import TagField
from tagging.models import Tag
from videologue.models import Video, YouTubeVideo


def remove_media_root(path):
    return path.replace(settings.MEDIA_ROOT, '')


class Publication(Model):
    name = CharField(u'nombre', max_length=100)
    twitter_username = CharField(
        u'Nombre de usuario de Twitter',
        max_length=15,
        blank=True,
        null=True,
        help_text=u'Nombre de usuario de Twitter que se menciona cuando artículos de esta publicación son compartidos '
                  u'en Twitter (escribir sin @)',
    )
    description = TextField(
        u'descripción', null=True, blank=True, help_text=u'Se muestra en el componente de portada.'
    )
    slug = SlugField(u'slug', unique=True)
    headline = CharField(u'título', max_length=100)
    weight = PositiveSmallIntegerField(u'orden', default=0)
    public = BooleanField(u'público', default=True)
    has_newsletter = BooleanField(u'tiene NL', default=False)
    newsletter_name = CharField(max_length=64, blank=True, null=True)
    newsletter_tagline = CharField(max_length=128, blank=True, null=True)
    newsletter_periodicity = CharField(max_length=64, blank=True, null=True)
    newsletter_header_color = CharField(u'color de cabezal para NL', max_length=7, default=u'#262626')
    newsletter_campaign = CharField(max_length=64, blank=True, null=True)
    subscribe_box_question = CharField(max_length=64, blank=True, null=True)
    subscribe_box_nl_subscribe_auth = CharField(max_length=128, blank=True, null=True)
    subscribe_box_nl_subscribe_anon = CharField(max_length=128, blank=True, null=True)
    image = ImageField(u'logo / Logo para NL', upload_to='publications', blank=True, null=True)
    full_width_cover_image = ForeignKey(Photo, verbose_name=u'foto full de portada', blank=True, null=True)
    is_emergente = BooleanField(u'es emergente', default=False)
    new_pill = BooleanField(u'pill de "nuevo" en el componente de portada', default=False)
    icon = CharField(max_length=128, blank=True, null=True)
    icon_png = CharField(max_length=128, blank=True, null=True)
    icon_png_16 = CharField(max_length=128, blank=True, null=True)
    icon_png_32 = CharField(max_length=128, blank=True, null=True)
    apple_touch_icon_180 = CharField(max_length=128, blank=True, null=True)
    apple_touch_icon_192 = CharField(max_length=128, blank=True, null=True)
    apple_touch_icon_512 = CharField(max_length=128, blank=True, null=True)
    open_graph_image = CharField(max_length=128, blank=True, null=True)
    open_graph_image_width = PositiveSmallIntegerField(blank=True, null=True)
    open_graph_image_height = PositiveSmallIntegerField(blank=True, null=True)
    publisher_logo = CharField(max_length=128, blank=True, null=True)
    publisher_logo_width = PositiveSmallIntegerField(blank=True, null=True)
    publisher_logo_height = PositiveSmallIntegerField(blank=True, null=True)

    def __unicode__(self):
        return self.name or u''

    def save(self, *args, **kwargs):
        super(Publication, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return urlresolvers.reverse(
            'home',
            kwargs={} if self.slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL else {'domain_slug': self.slug}
        )

    def latest_edition(self):
        return self.core_edition.latest()

    def get_menu_order(self):
        return getattr(settings, 'CORE_PUBLICATIONS_SECTIONS_MENU_ORDER', {}).get(self.slug)

    def primary_sections(self):
        menu_order = self.get_menu_order()
        return self.section_set.filter(home_order__lt=menu_order) if menu_order else self.section_set.all()

    def secondary_sections(self):
        menu_order = self.get_menu_order()
        if menu_order:
            return self.section_set.filter(home_order__gte=menu_order)

    def latest_articles(self):
        edition, cover_article = get_latest_edition(self), None
        try:
            cover_article = edition.articlerel_set.get(home_top=True, top_position=1).article
        except (ArticleRel.DoesNotExist, ArticleRel.MultipleObjectsReturned):
            pass
        top_arts = edition.top_articles[:12]
        top_arts.sort(key=operator.attrgetter('section.home_order'))
        return ([cover_article] + top_arts) if cover_article else top_arts

    def subscriber_count(self):
        return len(
            set(
                self.subscriber_set.filter(
                    user__is_active=True
                ).exclude(user__email='').values_list('user__email', flat=True)
            ) - blacklisted
        )
    subscriber_count.short_description = u'Suscrip. NL'

    def image_tag(self):
        url = None
        if self.image:
            logo_filename = self.image.path
            logo_image = Image.open(logo_filename)
            if logo_image.size[0] > 120:
                tmpfile, f = tempfile.mkstemp('.png', dir=settings.MEDIA_ROOT)
                logo_image.convert('RGB').save(f, optimize=True)
                url = get_thumbnail(f, '120', crop='center', quality=99).url
            else:
                url = u'%s%s' % (settings.MEDIA_URL, self.image)
        return (
            u'<a href="/admin/core/publication/%d/">'
            u'<img src="%s" style="background:%s;"/></a>' % (
                self.id, url, self.newsletter_header_color) if url else u'')
    image_tag.short_description = u'logo / Logo para NL'
    image_tag.allow_tags = True

    def get_full_width_cover_image_tag(self):
        return (
            u'<a href="/admin/core/publication/%d/">'
            u'<img src="%s" alt="%s"></a>' % (
                self.id, self.full_width_cover_image.get_admin_thumbnail_url(),
                self.full_width_cover_image) if self.full_width_cover_image
            else u'')
    get_full_width_cover_image_tag.short_description = u'foto full de portada'
    get_full_width_cover_image_tag.allow_tags = True

    class Meta:
        ordering = ['weight']
        verbose_name = u'publicación'
        verbose_name_plural = u'publicaciones'


class PortableDocumentFormatBaseModel(Model):
    pdf = FileField(
        u'archivo PDF',
        max_length=150,
        upload_to=get_pdf_pdf_upload_to,
        blank=True,
        null=True,
        help_text=u'<strong>AVISO:</strong> Si es mayor a 8MB probablemente no se pueda enviar por mail.',
    )
    pdf_md5 = CharField(u'checksum', max_length=32, editable=False)
    downloads = PositiveIntegerField(u'descargas', default=0)
    cover = ImageField(u'tapa', upload_to=get_pdf_cover_upload_to, blank=True, null=True)
    date_published = DateField(u'fecha de publicación', default=timezone.now)
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True)

    def __unicode__(self):
        return self.pdf[self.pdf.rfind('/') + 1:]

    class Meta:
        abstract = True
        get_latest_by = 'date_published'
        ordering = ('-date_published', )

    def get_pdf_filename(self):
        return None

    def get_cover_filename(self):
        return '%s.jpg' % self.get_pdf_filename()[:-4]

    @permalink
    def get_download_url(self):
        return 'edition_download', (), {
            'publication_slug': self.publication.slug,
            'year': self.date_published.year,
            'month': u'%02d' % self.date_published.month,
            'day': u'%02d' % self.date_published.day,
            'filename': os.path.basename(self.pdf.path)}

    def download(self, request=None):
        try:
            response = HttpResponse(self.pdf, content_type='application/pdf')
        except IOError:
            raise Http404
        else:
            response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(self.pdf.path)
            return response


""" TODO: better enable this after new structure works well (**)
class EditionSection(models.Model):
    edition = ForeignKey(Edition)
    section = ForeignKey(Section)
    home_order = PositiveSmallIntegerField(u'orden en Portada', default=0)
    in_home = BooleanField(u'mostrar_en_portada', default=True)
    style = CharField(
        u'estilo', max_length=2, choices=STYLE_CHOICES, blank=True, null=True)
"""


class Edition(PortableDocumentFormatBaseModel):
    """An edition of the newspaper."""
    title = TextField(u'título', null=True)
    publication = ForeignKey(
        Publication, verbose_name=u'publicación',
        related_name="%(app_label)s_%(class)s")
    # (**) sections = ManyToManyField(Section, through='EditionSection')

    class Meta(PortableDocumentFormatBaseModel.Meta):
        verbose_name = u'edición'
        verbose_name_plural = u'ediciones'

    def __unicode__(self):
        try:
            display_name = u'%s - %s' % (
                self.date_published.strftime('%d-%m-%Y'),
                self.publication.name)
        except Exception:
            display_name = self.date_published.strftime('%d-%m-%Y')
        return display_name

    def edition_pub(self):
        return str(self)
    edition_pub.short_description = 'Fecha publicada'

    def get_supplements(self):
        return self.supplements.values_list('pdf', 'cover') or u''
    get_supplements.short_description = u'suplementos'

    def get_absolute_url(self):
        reverse_kwargs = {
            'year': self.date_published.year, 'month': self.date_published.month, 'day': self.date_published.day}
        if self.publication and self.publication.slug not in settings.CORE_PUBLICATIONS_USE_ROOT_URL:
            reverse_kwargs['publication_slug'] = self.publication.slug
        return urlresolvers.reverse('edition_detail', kwargs=reverse_kwargs)

    def published_articles(self):
        return Article.objects.filter(
            is_published=True
        ).extra(
            where=['core_article.id=core_articlerel.article_id', 'core_articlerel.edition_id=%d' % self.id],
            tables=['core_articlerel'],
        ).order_by('articlerel__top_position').distinct()

    def newsletter_featured_articles(self):
        return self.published_articles().filter(newsletter_featured=True)

    def get_pdf_filename(self):
        return '%s-%s.pdf' % (self.publication.slug, self.date_published.strftime('%Y%m%d'))

    @property
    def top_articles(self):
        return list(OrderedDict.fromkeys([ar.article for ar in self.articlerel_set.prefetch_related(
            'article__main_section__edition__publication', 'article__main_section__section',
            'article__photo__extended__photographer'
        ).filter(article__is_published=True, home_top=True).order_by('top_position')]))

    def get_articles_in_section(self, section):
        return list(OrderedDict.fromkeys([ar.article for ar in self.articlerel_set.select_related(
            'article__main_section__edition__publication', 'article__main_section__section',
            'article__photo__extended__photographer'
        ).filter(article__is_published=True, section=section).order_by('position')]))

    def previous_section(self, section):
        editions = [ar.edition for ar in ArticleRel.objects.filter(
            section=section,
            edition__date_published__lt=self.date_published).order_by(
            '-edition__date_published')]
        return editions[0] if editions else None

    @property
    def previous_edition(self):
        try:
            return Edition.objects.filter(
                date_published__lt=self.date_published
            ).order_by('-date_published')[0]
        except Exception:
            return None

    @property
    def next_edition(self):
        try:
            return Edition.objects.filter(
                date_published__gt=self.date_published,
                date_published__lte=date.today()).order_by('date_published')[0]
        except Exception:
            return None


class Supplement(PortableDocumentFormatBaseModel):
    SUPPLEMENT_NAME_CHOICES = (
        ('cc', u'Cambio Climático'),
        ('ag', u'Agenda Global'),
        ('br', u'Brasil'),
        ('cn', u'Cine nacional'),
        ('cp', u'Ciudad puerto'),
        ('cu', u'Cumbre'),
        ('di', u'Dínamo'),
        ('ed', u'Educación'),
        ('uv', u'El Uruguay que viene'),
        ('el', u'Elecciones'),
        ('en', u'Energía'),
        ('hp', u'El mundo hecho pelota'),
        ('in', u'Incorrecta'),
        ('iv', u'IVC'),
        ('lf', u'la diaria del futuro'),
        ('le', u'Lento'),
        ('li', u'Los informantes'),
        ('ec', u'Ecología'),
        ('ma', u'Medio ambiente'),
        ('me', u'Mercosur'),
        ('pa', u'Patrimonio'),
        ('rr', u'R'),
        ('rl', u'Radios Locas'),
        ('rn', u'RÑ'),
        ('sa', u'Salud'),
        ('tc', u'Tarjeta cultural'),
        ('ts', u'Teatro Solís'),
        ('yf', u'Yo firmé'),
        ('dm', u'Día Mundial del Agua'),
        ('al', u'א - Cultura Científica'),
        ('ns', u'nosotros'),
        ('df', u'día del futuro'),
        ('dd', u'Día Internacional del Detenido Desaparecido'),
        ('af', u'Agenda del Día del Futuro'),
    )
    edition = ForeignKey(
        Edition, verbose_name=u'edición', related_name='supplements')
    name = CharField(u'nombre', max_length=2, choices=SUPPLEMENT_NAME_CHOICES)
    slug = SlugField(u'slug', unique=True)
    headline = CharField(u'titular', max_length=100)
    public = BooleanField(u'público', default=True)

    class Meta:
        get_latest_by = 'date_published'
        ordering = ('-date_published', 'name')
        unique_together = ('date_published', 'name')
        verbose_name = u'suplemento'
        verbose_name_plural = u'suplementos'

    def __unicode__(self):
        return u'%s - %s' % (self.date_published.strftime('%d-%m-%Y'), self.get_name_display())

    def save(self, *args, **kwargs):
        self.date_published = self.edition.date_published
        self.slug = self.get_slug()
        super(Supplement, self).save(*args, **kwargs)

    def get_slug(self):
        name_slug, x = slugify(self.get_name_display()), 1
        queryset = self.__class__.objects.all()
        if self.id:
            if self.slug.startswith(name_slug + '-'):
                return self.slug
        while queryset.filter(slug='%s-%i' % (name_slug, x)).count():
            x += 1
        return '%s-%i' % (name_slug, x)

    @permalink
    def get_absolute_url(self):
        return 'supplement_detail', (), {
            'supplement_slug': self.slug, 'year': self.date_published.year,
            'month': self.date_published.month, 'day': self.date_published.day}

    def get_pdf_filename(self):
        return '%s-%s-%s.pdf' % (
            self.edition.get_name_display().replace(' ', '_'),
            self.date_published.strftime('%Y%m%d'),
            self.slug.replace('-', '_'))

    def get_pdf_url(self):
        try:
            return self.pdf.url
        except Exception:
            return ""


class Category(Model):
    name = CharField(u'nombre', max_length=16, unique=True)
    slug = CharField(u'slug', max_length=16, blank=True, null=True)
    description = TextField(u'descripción', blank=True, null=True)
    order = PositiveSmallIntegerField(u'orden', blank=True, null=True)
    has_newsletter = BooleanField(u'tiene NL', default=False)
    newsletter_tagline = CharField(max_length=128, blank=True, null=True)
    newsletter_periodicity = CharField(max_length=64, blank=True, null=True)
    subscribe_box_question = CharField(max_length=64, blank=True, null=True)
    subscribe_box_nl_subscribe_auth = CharField(max_length=128, blank=True, null=True)
    subscribe_box_nl_subscribe_anon = CharField(max_length=128, blank=True, null=True)
    title = CharField(u'título en el componente de portada', max_length=50, blank=True, null=True)
    more_link_title = CharField(
        u'texto en el link "más" del componente de portada', max_length=50, blank=True, null=True
    )
    new_pill = BooleanField(u'pill de "nuevo" en el componente de portada', default=False)
    full_width_cover_image = ForeignKey(Photo, verbose_name=u'foto full de portada', blank=True, null=True)
    full_width_cover_image_title = CharField(
        u'título para foto full',
        max_length=50,
        null=True,
        blank=True,
        help_text=u'Se muestra sólo si la foto está seteada. (Máx 50 caract.)',
    )
    full_width_cover_image_lead = TextField(
        u'bajada para foto full',
        null=True,
        blank=True,
        help_text=u'Se muestra sólo si la foto y el título están seteados.',
    )
    exclude_from_top_menu = BooleanField(u'Excluir ítem en menú superior de escritorio', default=False)

    def __unicode__(self):
        return self.name

    def latest_articles(self):
        return list(self.home.articles.all()) if hasattr(self, 'home') else []

    def articles(self):
        """
        Returns all articles published on this category
        """
        return Article.objects.filter(id__in=[
            a.id for a in Article.objects.raw("""
            SELECT core_article.id
            FROM core_article
            JOIN core_articlerel ON
                core_article.id = core_articlerel.article_id
            JOIN core_section ON
                core_articlerel.section_id = core_section.id
            WHERE core_section.category_id = %d AND is_published
            GROUP BY core_article.id ORDER BY date_published DESC
        """ % self.id)])

    # TODO: check if these mas_leidos* methods are still beeing used, because the "home" component and /masleidos url
    #       were migrated to views.
    def mas_leidos(self, days=1):
        """
        Returns the top 9 most viewed articles counting days days ago from now
        """
        since = datetime.now() - timedelta(days)
        return Article.objects.raw("""
            SELECT core_article.id
            FROM core_article
            JOIN core_articlerel ON
                core_article.id = core_articlerel.article_id
            JOIN core_section ON
                core_articlerel.section_id = core_section.id
            WHERE core_section.category_id = %d AND is_published AND
                  date_published > '%s'
            GROUP BY core_article.id ORDER BY views DESC LIMIT 9
        """ % (self.id, since))

    def mas_leidos_daily(self):
        days_ago = 1 if date.today().isoweekday() < 7 else 2
        return self.mas_leidos(days_ago)

    def mas_leidos_weekly(self):
        return self.mas_leidos(7)

    def mas_leidos_monthly(self):
        return self.mas_leidos(30)

    def subscriber_count(self):
        return len(
            set(
                self.subscriber_set.filter(
                    user__is_active=True
                ).exclude(user__email='').values_list('user__email', flat=True)
            ) - blacklisted
        )
    subscriber_count.short_description = u'Suscrip. NL'

    def get_full_width_cover_image_tag(self):
        return (
            u'<a href="/admin/core/category/%d/">'
            u'<img src="%s" alt="%s"></a>' % (
                self.id, self.full_width_cover_image.get_admin_thumbnail_url(),
                self.full_width_cover_image) if self.full_width_cover_image
            else u'')

    get_full_width_cover_image_tag.short_description = u'foto full de portada'
    get_full_width_cover_image_tag.allow_tags = True

    def get_absolute_url(self):
        return urlresolvers.reverse('home', kwargs={'domain_slug': self.slug})

    class Meta:
        verbose_name = u'área'
        ordering = ('order', 'name')


class Section(Model):
    SECTION_1 = '1'
    SECTION_2 = '2'
    SECTION_3 = '3'

    category = ForeignKey(Category, verbose_name='área', blank=True, null=True)
    name = CharField(u'nombre', max_length=50, unique=True)
    name_in_category_menu = CharField(u'nombre en el menú del área', max_length=50, blank=True, null=True)
    slug = SlugField(u'slug', unique=True)
    description = TextField(u'descripción', blank=True, null=True)
    contact = EmailField(u'correo electrónico', blank=True, null=True)
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True)
    home_order = PositiveSmallIntegerField(u'orden en portada', default=0)
    in_home = BooleanField(
        u'en portada', default=False,
        help_text=u'si el componente de portadas de esta categoría está insertado, esta opción lo muestra u oculta.')
    imagen = ImageField(u'imagen o ilustración', upload_to='section_images', blank=True, null=True)
    publications = ManyToManyField(Publication, verbose_name=u'publicaciones', blank=True)
    home_block_all_pubs = BooleanField(
        u'usar todas las publicaciones en módulos de portada', default=True,
        help_text=u'Marque esta opción para mostrar artículos de todas las publicaciones en los módulos de portada.')
    home_block_show_featured = BooleanField(
        u'mostrar artículos destacados en módulos de portada', default=True,
        help_text=u'Marque esta opción para mostrar artículos destacados en los módulos de portada.')
    background_color = CharField(u'background color', max_length=7, default='#ffffff')
    white_text = BooleanField(u'texto blanco', default=False)
    show_description = BooleanField(u'mostrar descripción', default=False)
    show_image = BooleanField(u'mostrar imagen', default=False)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Section, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return urlresolvers.reverse('section_detail', kwargs={'section_slug': self.slug})

    def is_satirical(self):
        return self.slug in getattr(settings, 'CORE_SATIRICAL_SECTIONS', ())

    def get_publications(self):
        return u', '.join(self.publications.values_list('name', flat=True))
    get_publications.short_description = u'publicaciones'

    def get_tags(self):
        return Tag.objects.get_for_object(self)

    def latest(self, limit=4, all_sections=False, article_type=None, exclude_articles_ids=[], publications_ids=[]):
        """
        Returns the latest 4 (or limit param) articles published in this section.
        - include only articles of this article_type (if given).
        - exclude articles by id included in a list given by param.
        - include only articles published only in editions of the publications included in a list given by param.
        - include articles related to any section and not only this (self) section if all_sections=True.
        NOTE: ordering by position is not applied because this method can take articles in more than one edition and
              the position is an ordering that makes sense only inside a section in one edition.
        """
        extra_where = ''

        if not all_sections:
            extra_where = ' AND core_articlerel.section_id=%s' % self.id

        if article_type:
            extra_where += " AND core_article.type='%s'" % article_type

        if exclude_articles_ids:
            extra_where += ' AND core_article.id NOT IN (%s)' % ','.join([str(x) for x in exclude_articles_ids])

        if publications_ids:
            extra_where += ' AND core_edition.publication_id IN (%s)' % ','.join([str(x) for x in publications_ids])

        query = """
            SELECT core_article.id
            FROM core_article
                JOIN core_articlerel ON core_article.id = core_articlerel.article_id
                JOIN core_edition ON core_articlerel.edition_id = core_edition.id
            WHERE is_published%s
            GROUP BY id
            ORDER BY core_article.date_published DESC
            LIMIT %s
        """ % (extra_where, limit)

        if settings.RAW_SQL_DEBUG:
            print(query)

        return Article.objects.raw(query)

    def latest3(self):
        """
        Returns the latest 3 articles published in this section. Called from news_wall.html.
        """
        return self.latest(3)

    def latest4related(self, exclude_id):
        """
        devuelve los últimos 4 articulos de la sección que acepten ser
        relacionados excluyendo al que se le pasa por parametro.
        """
        return Article.objects.raw("""
            SELECT core_article.*
            FROM core_article JOIN core_articlerel
                ON core_article.id = core_articlerel.article_id
            WHERE core_articlerel.section_id=%s AND is_published
                AND allow_related AND core_article.id!=%s
            GROUP BY id ORDER BY date_published DESC
            LIMIT 4""" % (self.id, exclude_id))

    def latest4relatedbycategory(self, category, exclude_id):
        """
        devuelve los últimos 4 articulos de la categoría que acepten ser
        relacionados excluyendo al que se le pasa por parametro.
        """
        return Article.objects.raw("""
            SELECT core_article.*
            FROM core_article JOIN core_articlerel
                ON core_article.id = core_articlerel.article_id
                JOIN core_section
                ON core_articlerel.section_id = core_section.id
            WHERE is_published AND allow_related
                AND core_section.category_id=%s AND core_article.id!=%s
            GROUP BY id ORDER BY date_published DESC
            LIMIT 4""" % (category, exclude_id))

    def latest4relatedbypublication(self, publication, exclude_id):
        """
        devuelve los últimos 4 articulos de la publicacion que acepten ser
        relacionados excluyendo al que se le pasa por parametro.
        """
        return Article.objects.raw("""
            SELECT a.* FROM core_article a JOIN core_articlerel ar ON a.id=ar.article_id
                JOIN core_edition e ON ar.edition_id=e.id
            WHERE a.is_published AND a.allow_related AND e.publication_id=%s AND a.id!=%s
            GROUP BY a.id ORDER BY a.date_published DESC LIMIT 4""" % (publication, exclude_id)) \
            if settings.CORE_ENABLE_RELATED_ARTICLES else []

    def latest_article(self):
        """
        Returns the latest article (by article's date_published) published in this section.
        TODO: This method is called from send_category_nl.py, section.py and category.py and all this calls can raise
              IndexError if this method returns an empty list.
        """
        latest_qs = self.articlerel_set.filter(article__is_published=True).order_by('-article__date_published')
        return [latest_qs[0].article] if latest_qs.exists() else []

    def mas_vistos(self):
        desde = datetime.now() - timedelta(days=60)
        return Article.objects.filter(
            sections__id=self.id, date_published__gt=desde
        ).order_by('views')[:10]

    def latest_articles(self):
        """
        Returns this section's articles in the last 24 hours (or 48 on sundays)
        """
        return self.articles_core.filter(
            is_published=True, date_published__gt=datetime.now() - timedelta(
                2 if date.today().isoweekday() < 7 else 3)
        ).distinct()

    def articles_count(self):
        return self.articles_core.count()
    articles_count.short_description = u'# Artículos'

    class Meta:
        get_latest_by = 'date_created'
        ordering = ('home_order', 'name', 'date_created')
        verbose_name = u'sección'
        verbose_name_plural = u'secciones'


class Journalist(Model):

    JOB_CHOICES = (
        ('PE', u'Periodista'),
        ('CO', u'Columnista'),
    )

    name = CharField(u'nombre', max_length=50, unique=True)
    email = EmailField(u'correo electrónico', blank=True, null=True)
    slug = SlugField(u'slug', unique=True)
    image = ImageField(
        u'imagen', upload_to='journalist', blank=True, null=True)
    job = CharField(
        u'trabajo', max_length=2, choices=JOB_CHOICES, default='PE',
        help_text=u'Rol en que se desempeña principalmente.')
    bio = TextField(
        u'bio', null=True, blank=True, help_text=u'Bio aprox 200 caracteres.')
    sections = ManyToManyField(
        Section, verbose_name=u'secciones', blank=True)
    fb = CharField(u'facebook', max_length=255, blank=True, null=True)
    tt = CharField(u'twitter', max_length=255, blank=True, null=True)
    gp = CharField(u'google plus', max_length=255, blank=True, null=True)
    ig = CharField(u'instangram', max_length=255, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Journalist, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return urlresolvers.reverse(
            'journalist_detail', kwargs={
                'journalist_job': u'columnista' if self.job == 'CO' else u'periodista', 'journalist_slug': self.slug})

    def get_published(self):
        if self.job == 'PE':
            published = Article.objects.filter(byline__id=self.id)
        if self.job == "FO":
            published = PhotoExtended.objects.filter(byline__id=self.id)
        else:
            published = None
        return published

    def get_sections(self):
        return self.sections.all()

    class Meta:
        ordering = ('name', )
        verbose_name = u'periodista'
        verbose_name_plural = u'periodistas'


class Location(Model):
    city = CharField(u'ciudad', max_length=50)
    country = CharField(u'país', max_length=50)
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True)

    def __unicode__(self):
        return u'%s, %s' % (self.city, self.country)

    class Meta:
        get_latest_by = 'date_created'
        ordering = ('country', 'city')
        unique_together = ('city', 'country')
        verbose_name = u'ubicación'
        verbose_name_plural = u'ubicaciones'


class ArticleBase(Model, CT):
    FEATURE = 'FE'
    LOSINFORMANTES = 'LI'
    ELFARO = 'EF'
    NEWS = 'NE'
    OMBUDSMAN = 'OM'
    CARTAS = 'CL'
    OP_ED = 'OP'
    LENTO = 'LE'
    SUMMARY = 'SU'
    PHOTO_ARTICLE = 'PA'
    METRO_ARTICLE = 'MA'  # metro article
    SHORT_ARTICLE = 'SA'  # short article
    RECUADRO = 'RE'       # short article
    HTML = 'HT'
    COMUNIDAD = 'CM'

    TYPE_CHOICES = (
        (FEATURE, 'Variedad'),
        (LOSINFORMANTES, 'Los Informantes'),
        (ELFARO, 'El Faro del final del mundo'),
        (NEWS, 'Noticia'),
        (OMBUDSMAN, 'Defensor del lector'),
        (CARTAS, 'Cartas de lectores'),
        (OP_ED, 'Opinión'),
        (LENTO, 'Lento'),
        (SUMMARY, 'Sumario'),
        (PHOTO_ARTICLE, 'Fotografía'),
        (METRO_ARTICLE, 'Metro'),
        (SHORT_ARTICLE, 'Recuadro Breves'),
        (RECUADRO, 'Recuadro'),
        (HTML, 'HTML'),
        (COMUNIDAD, 'COMUNIDAD'),
    )

    DISPLAY_CHOICES = (
        ('I', u'Imagen'),
        ('A', u'Audio'),
        ('V', u'Video'),
    )

    HEADER_DISPLAY_CHOICES = (
        ('FW', u'Ancho completo'),
        ('BG', u'Grande'),
    )

    HOME_HEADER_DISPLAY_CHOICES = (
        ('FW', u'Ancho completo'),
        ('FF', u'Medio y medio'),
        ('SM', u'Chico'),
    )

    publication = ForeignKey(
        Publication,
        verbose_name=u'publicación',
        blank=True,
        null=True,
        related_name='articles_%(app_label)s',
    )
    type = CharField(u'tipo', max_length=2, choices=TYPE_CHOICES, blank=True, null=True)
    headline = CharField(u'título', max_length=200, help_text=u'Se muestra en la portada y en la nota.')
    keywords = CharField(
        u'titulín', max_length=45, blank=True, null=True, help_text=u'Se muestra encima del título en portada.'
    )
    slug = SlugField(u'slug', max_length=200)
    url_path = CharField(max_length=512, db_index=True)
    deck = TextField(
        u'bajada', blank=True, null=True, help_text=u'Se muestra en la página de la nota debajo del título.'
    )
    lead = TextField(
        u'copete', blank=True, null=True, help_text=u'Se muestra en la página de la nota debajo de la bajada.'
    )
    body = TextField(u'cuerpo')
    header_display = CharField(
        u'tipo de cabezal', max_length=2, choices=HEADER_DISPLAY_CHOICES, blank=True, null=True, default='BG'
    )
    home_header_display = CharField(
        u'tipo de cabezal cuando es portada',
        max_length=2,
        choices=HOME_HEADER_DISPLAY_CHOICES,
        blank=True,
        null=True,
        default='SM',
    )
    home_lead = TextField(u'bajada en portada', blank=True, null=True, help_text=u'Bajada de la nota en portada.')
    home_display = CharField(u'mostrar en portada', max_length=2, choices=DISPLAY_CHOICES, blank=True, null=True)
    home_top_deck = TextField(
        u'bajada en destacados',
        blank=True,
        null=True,
        help_text=(
            u'Se muestra en los destacados de la portada, en el caso de estar vació se muestra la bajada de la nota.'
        ),
    )
    byline = ManyToManyField(
        Journalist,
        verbose_name=u'autor/es',
        related_name='articles_%(app_label)s',
        blank=True,
    )
    only_initials = BooleanField(
        u'sólo iniciales',
        default=False,
        help_text=(
            u'Marque esta opción para que en la firma del artículo se muestren únicamente las iniciales del autor.'
        ),
    )
    latitude = DecimalField(u'latitud', max_digits=10, decimal_places=6, blank=True, null=True)
    longitude = DecimalField(u'longitud', max_digits=10, decimal_places=6, blank=True, null=True)
    location = ForeignKey(
        Location,
        verbose_name=u'ubicación',
        related_name='articles_%(app_label)s',
        blank=True,
        null=True,
    )
    is_published = BooleanField(u'publicado', default=True)
    date_published = DateTimeField(u'fecha de publicación', blank=False, null=False, default=timezone.now)
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True)
    last_modified = DateTimeField(u'última actualización', auto_now=True)
    views = PositiveIntegerField(u'vistas', default=0, db_index=True)
    allow_comments = BooleanField(u'Habilitar comentarios', default=True)
    created_by = ForeignKey(
        User,
        verbose_name=u'creado por',
        related_name='created_articles_%(app_label)s',
        editable=False,
        blank=False,
        null=True,
    )
    photo = ForeignKey(Photo, blank=True, null=True, verbose_name=u'imagen')
    gallery = ForeignKey(Gallery, verbose_name=u'galería', blank=True, null=True)
    video = ForeignKey(
        Video,
        verbose_name=u'video',
        related_name='articles_%(app_label)s',
        blank=True,
        null=True,
    )
    youtube_video = ForeignKey(YouTubeVideo, verbose_name=u'video de YouTube', blank=True, null=True)
    audio = ForeignKey(
        Audio,
        verbose_name=u'audio',
        related_name='articles_%(app_label)s',
        blank=True,
        null=True,
    )
    tags = TagField(verbose_name=u'etiquetas', blank=True, null=True)
    allow_related = BooleanField(
        u'mostrar en artículos relacionados', default=True, blank=False, null=False, db_index=True
    )
    show_related_articles = BooleanField(
        u'mostrar artículos relacionados dentro de este artículo', default=True, blank=False, null=False
    )
    public = BooleanField(u'Artículo libre', default=False)

    published = PublishedArticleManager()

    def __unicode__(self):
        return self.headline

    def save(self, *args, **kwargs):
        from utils import add_punctuation
        if not self.id:
            month, year = (self.date_published.month, self.date_published.year)
            if Article.objects.filter(
                    slug=self.slug, date_published__month=month,
                    date_published__year=year).count():
                # FIXME: Morir de manera más digna.
                raise Exception
        for attr in ('headline', 'deck', 'lead', 'body'):
            if getattr(self, attr, None):
                setattr(self, attr, getattr(self, attr).strip())
                setattr(self, attr, smart_quotes(getattr(self, attr)))
        for attr in ('deck', 'lead', 'body'):
            if getattr(self, attr, None):
                setattr(self, attr, add_punctuation(getattr(self, attr, '')))

        self.slug = slugify(cleanhtml(ldmarkup(self.headline)))
        if self.is_published and not settings.DEBUG:
            try:
                ping_google()
            except Exception:
                pass

        super(ArticleBase, self).save(*args, **kwargs)

    def is_photo_article(self):
        return self.type == self.PHOTO_ARTICLE

    def has_deck(self):
        return bool(self.deck)

    def get_deck(self):
        if self.deck:
            return self.deck
        return ''

    def has_lead(self):
        return bool(self.lead)

    def get_lead(self):
        if self.lead:
            return self.lead
        elif self.type == 'SA' or self.type == 'RE':
            return self.body
        return self.body[:self.body.find('\n')]

    def get_keywords(self):
        if self.keywords:
            return self.keywords
        return None

    def has_byline(self):
        byline = ''
        for author in self.byline.all():
            byline += '%s, ' % author
        if byline == '':
            return False
        self.get_byline = byline[:-2]
        return True

    def get_authors(self):
        if self.byline:
            return list(self.byline.all())
        return None

    def get_tags(self):
        return Tag.objects.get_for_object(self)

    def get_absolute_url(self):
        return self.url_path or self.build_url_path()  # TODO: remove this "or" after url paths saved for all articles

    def build_url_path(self):
        reverse_kwargs = {'year': self.date_published.year, 'month': self.date_published.month, 'slug': self.slug}
        main_section = getattr(self, 'main_section', None)
        if main_section:
            if main_section.edition.publication.slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL:
                if main_section.section.category:
                    reverse_kwargs['domain_slug'] = main_section.section.category.slug
            else:
                reverse_kwargs['domain_slug'] = main_section.edition.publication.slug
        return urlresolvers.reverse('article_detail', kwargs=reverse_kwargs)

    def get_discussion_url(self):
        return '%sdiscusion/' % self.get_absolute_url()

    def get_comment_post_url(self):
        return self.get_discussion_url()

    def get_feed_url(self):
        return '/feeds/discusion/%(year)i/%(month)i/%(slug)s/' % \
            {'year': self.date_published.year,
             'month': self.date_published.month, 'slug': self.slug}

    def get_app_body(self):
        """ Returns the body formatted for the app """
        return render_to_string('article/app_body.html', {'article': self})

    def surl(self):
        return '<a href="/short/A/%i/">sURL</a>' % self.id
    surl.allow_tags = True

    @property
    def display(self):
        return str(self.cols) + 'x' + str(self.rows)

    @property
    def top_deck(self):
        if self.home_top_deck:
            return self.home_top_deck
        return self.deck

    def edit_link(self):
        if self.id:
            change_url = urlresolvers.reverse('admin:core_article_change', args=(self.id, ))
            return "<a href='%s' target='_blank'>Editar</a>" % change_url
        else:
            return u"No Existe"
    edit_link.allow_tags = True

    def is_public(self):
        return self.public

    def get_photos_wo_cover(self):
        return self.gallery.photos.exclude(
            id__exact=self.photo.id if self.photo else 0)

    def mas_leidos(self, days=1, cover=False):
        """
        Returns the top 10 most viewed articles counting days days ago from now
        If cover is True the "humor" section is excluded. (Issue4910)
        """
        desde = datetime.now() - timedelta(days)
        articles = Article.objects.filter(date_published__gt=desde)
        if cover:
            articles = articles.exclude(sections__slug__contains="humor")
        return articles.order_by('-views')[:9]

    def mas_leidos_daily(self, cover=False):
        days_ago = 1 if date.today().isoweekday() < 7 else 2
        return self.mas_leidos(days_ago, cover)

    def mas_leidos_weekly(self, cover=False):
        return self.mas_leidos(7, cover)

    def mas_leidos_monthly(self, cover=False):
        return self.mas_leidos(30, cover)

    def masleidos_cover_daily(self):
        return self.mas_leidos_daily(True)

    def masleidos_cover_weekly(self):
        return self.mas_leidos_weekly(True)

    def masleidos_cover_monthly(self):
        return self.mas_leidos_monthly(True)

    def has_photo(self):
        try:
            return bool(self.photo)
        except PhotoExtended.DoesNotExist:
            return False

    def photo_image_file_exists(self):
        try:
            result = bool(self.photo.image.file)
        except IOError:
            result = False
        return result

    def gallery_photos(self):
        """
        Return only those photos whose image file exists
        """
        result = []
        for photo in self.gallery.photos.all():
            try:
                bool(photo.image.file)
            except IOError:
                continue
            else:
                result.append(photo)

        return result

    def unformatted_headline(self):
        return cleanhtml(ldmarkup(self.headline))

    def unformatted_deck(self):
        return cleanhtml(ldmarkup(self.deck))

    def unformatted_lead(self):
        return cleanhtml(ldmarkup(self.lead))

    def reading_time(self):
        """
           Based on article body text, returns the reading time of the article.
           Rounds down, so 65 seconds are rounded to 1 min.
           Assumes that body is in Markdown format. (simple text, and html
           are also available)

           Examples: * menos de un minuto
                     * 1 min
                     * 3 min
        """
        wpm = 250
        result = readtime.of_markdown(self.body, wpm=wpm)
        art_sec = result.seconds

        exts_sec = 0
        for extension in self.extensions.all():
            ext_res = readtime.of_markdown(extension.body, wpm=wpm)
            exts_sec = exts_sec + ext_res.seconds

        total_sec = art_sec + exts_sec
        if total_sec < 60:
            return 'Menos de 1 minuto'
        elif 60 <= total_sec and total_sec <= 119:
            return '1 minuto'
        else:
            mins = str(total_sec / 60) + ' minutos'
            return mins

    class Meta:
        abstract = True
        get_latest_by = 'date_published'
        ordering = ('-date_published', )
        verbose_name = u'artículo'
        verbose_name_plural = u'artículos'


class ArticleManager(Manager):
    def get_queryset(self):
        return super(ArticleManager, self).get_queryset()


class Article(ArticleBase):
    objects = ArticleManager()
    sections = ManyToManyField(
        Section,
        verbose_name=u'sección',
        blank=False,
        through='ArticleRel',
        related_name='articles_%(app_label)s',
    )
    main_section = ForeignKey(
        'ArticleRel',
        verbose_name=u'publicación principal',
        blank=True,
        null=True,
        related_name='main',
        on_delete=SET_NULL,
    )
    viewed_by = ManyToManyField(
        User,
        verbose_name=u'visto por',
        blank=True,
        editable=False,
        through='ArticleViewedBy',
        related_name='viewed_articles_%(app_label)s',
    )
    newsletter_featured = BooleanField(u'destacado en newsletter', default=False)

    def save(self, *args, **kwargs):
        try:
            super(Article, self).save(*args, **kwargs)
        except Exception:
            # we dont know why sometimes raises duplicate entry XXXX for key K
            # I cant reproduce this error, better to do nothing more in method
            return
        if self.sections:
            # TODO: this should be reviewed, what happens if another article
            # in the same edition-section is viewed (viewed implies saving)
            for ar in ArticleRel.objects.filter(article=self):
                if not ar.position:
                    ar.position = ArticleRel.objects.filter(edition=ar.edition, section=ar.section).count() + 1

        # TODO: also this if block should be reviewed (broken)
        # if self.home_top and self.top_position is None:
        #    self.top_position = Article.objects.filter(
        #        edition=self.edition, home_top=self.home_top).count() + 1
        if self.type == ArticleBase.HTML:
            self.headline = u'HTML | %s | %s | %s' % (
                unicode(self.edition), unicode(self.section), str(self.section_position)
            )

        super(Article, self).save(*args, **kwargs)

    def publications(self):
        return set([ar.edition.publication for ar in self.articlerel_set.select_related('edition__publication')])

    def get_publications(self):
        return ', '.join([p.name for p in self.publications()])
    get_publications.short_description = u'publicaciones'

    @property
    def section(self):
        if self.main_section:
            return self.main_section.section
        else:
            s = self.sections.all()[:1]
            return s[0] if s else None

    def last_published_by_category(self, category):
        """
        Returns the last date published of the article inside a section that
        has the category passed by param. If no editions found, return the
        article's date_published.
        """
        if self.is_published:
            try:
                result = Edition.objects.filter(id__in=[
                    v[0] for v in ArticleRel.objects.filter(
                        article=self, section__in=category.section_set.all()
                    ).values_list('edition')]
                ).order_by('-date_published')[0].date_published
            except IndexError:
                result = self.date_published.date()
            return result

    def publication_section(self, publication=None):

        if self.main_section:

            if not publication or self.main_section.edition.publication == publication:
                # No pub given or pub matches main_section => return main section
                return self.main_section.section
            else:
                # Return the first match, if no matches return the main section
                s = self.articlerel_set.filter(edition__publication=publication)[:1]
                return s[0].section if s else self.main_section.section

        elif self.sections.exists():

            if publication:
                # Return the first match with the pub given or the first if no matches
                s = self.articlerel_set.filter(edition__publication=publication)[:1]
                return s[0].section if s else self.sections.all()[0]

            else:
                # Return the first
                return self.sections.all()[0]

    def get_sections(self):
        return ', '.join([s.name for s in self.sections.distinct()])
    get_sections.short_description = u'secciones'

    def get_categories_slugs(self):
        return set([
            s.category.slug for s in self.sections.filter(
                category__isnull=False).distinct().select_related('category')])

    def get_app_photo(self):
        """
        Returns the article's photo if any, if not, returns the article's
        section image (if any)
        """
        if self.photo:
            return self.photo
        else:
            section_imgs = self.sections.filter(
                imagen__isnull=False).values_list('imagen', flat=True)
            if section_imgs:
                return PhotoExtended(image=section_imgs[0])


class ArticleRel(Model):
    """
    Relation to save the relative position of the article into the Article-Edition-Section relationship.
    NOTE: position cannot be blank because new rows marked as "main" in the admin inline, with position blank, and
          duplicated with another row (unique_together allows null values) will cause a 500 error when trying to set
          the row as main (another row can exist).
    """
    article = ForeignKey(Article)
    edition = ForeignKey(Edition)
    section = ForeignKey(Section)
    position = PositiveSmallIntegerField(u'orden en la sección', default=None, null=True)
    home_top = BooleanField(
        u'destacado en portada',
        default=False,
        help_text=u'Marque esta opción para que esta nota aparezca en los destacados de la edición.',
    )
    top_position = PositiveSmallIntegerField(u'orden', blank=True, null=True)

    def __unicode__(self):
        return u'%s - %s' % (self.edition, self.section)

    class Meta:
        ordering = ('position', '-article__date_published')
        unique_together = ('article', 'edition', 'section', 'position')


class ArticleViewedBy(Model):
    article = ForeignKey(Article)
    user = ForeignKey(User)
    viewed_at = DateTimeField(db_index=True)

    class Meta:
        unique_together = ('article', 'user')


class CategoryHomeArticle(Model):
    home = ForeignKey('CategoryHome')
    article = ForeignKey(Article, related_name='home_articles')
    position = PositiveSmallIntegerField('publicado')  # a custom label useful in the CategoryHome admin change form
    fixed = BooleanField('fijo', default=False)

    def __unicode__(self):
        # also a custom text version to be useful in the CategoryHome admin change form
        return u'%s' % self.article.last_published_by_category(self.home.category)

    class Meta:
        ordering = ('position', )


class CategoryHome(Model):
    category = OneToOneField(Category, verbose_name=u'área', related_name='home')
    articles = ManyToManyField(Article, through=CategoryHomeArticle)

    def __unicode__(self):
        return u'%s - %s' % (self.category, self.cover())

    def cover(self):
        """ Returns the article in the 1st position """
        return self.articles.exists() and self.articles.order_by('home_articles')[0]

    def non_cover_articles(self):
        """ Returns the articles from 2nd position """
        return self.articles.order_by('home_articles')[1:] if self.articles.exists() else []

    def set_article(self, article, position):
        try:
            actual_article = CategoryHomeArticle.objects.get(home=self, position=position)
            if actual_article.article != article:
                actual_article.article = article
                actual_article.save()
        except CategoryHomeArticle.DoesNotExist:
            CategoryHomeArticle.objects.create(home=self, article=article, position=position)

    class Meta:
        verbose_name = u'portada de área'
        verbose_name_plural = u'portadas de área'
        ordering = ('category', )


def update_category_home(dry_run=False):
    """
    Updates categories homes based on articles dates
    """
    # fill each category bucket with latest articles.
    # @dry_run: Do not change anything. It forces a debug message when a change would be made.
    # TODO: calculate not fixed count before and better stop algorithm.
    buckets, category_sections, needed, stop = {}, {}, 11, False
    categories = Category.objects.filter(slug__in=settings.CORE_UPDATE_CATEGORY_HOMES)

    for cat in categories:
        buckets[cat.slug] = []
        category_sections[cat.slug] = cat.section_set.all()

    if categories:
        if settings.DEBUG:
            print('DEBUG: update_category_home begin')
        for edition in Edition.objects.order_by('-date_published').iterator():

            for ar in ArticleRel.objects.filter(edition=edition).select_related('article').iterator():

                article = ar.article
                if article.is_published:

                    if any([len(b) < needed for b in buckets.values()]):
                        # fill category buckets with articles
                        # limiting upto needed quantity with no dupe articles
                        article_sections = set(article.sections.filter(articlerel__edition=edition))
                        for cat in categories:
                            if len(buckets[cat.slug]) < needed and \
                                    article not in [x[0] for x in buckets[cat.slug]] and \
                                    article_sections.intersection(category_sections[cat.slug]):
                                buckets[cat.slug].append((article, edition.date_published))
                    else:
                        stop = True
                        break

            if stop:
                break

    # iterate over the buckets and compute free places to fill
    for category_slug, articles in buckets.items():
        category = categories.get(slug=category_slug)

        try:
            home = category.home
        except CategoryHome.DoesNotExist:
            continue

        try:
            home_cover = CategoryHomeArticle.objects.get(home=home, position=1)
        except CategoryHomeArticle.DoesNotExist:
            home_cover = None
        cover_id = home_cover.article_id if home_cover else None
        cover_fixed = home_cover.fixed if home_cover else False
        cover_date = home_cover.article.last_published_by_category(category) if home_cover else None
        if cover_fixed:
            category_fixed_content = {cover_id: (0, cover_fixed, cover_date, home_cover.article)}
            category_free_content = {}
        else:
            category_fixed_content = {}
            category_free_content = {cover_id: (0, cover_id, cover_date)}
        free_places = [0] if category_free_content else []

        try:
            for i in range(2, needed):
                try:
                    position_i = CategoryHomeArticle.objects.get(home=home, position=i)
                    a = position_i.article
                    aid, afixed = a.id, position_i.fixed
                    date_published = a.last_published_by_category(category)
                    if afixed:
                        category_fixed_content[aid] = (i, afixed, date_published, a)
                    else:
                        category_free_content[aid] = (i, aid, date_published)
                        free_places.append(i)
                except CategoryHomeArticle.DoesNotExist:
                    free_places.append(i)

        except IndexError:
            pass

        # if not free places nothing will be done, then continue
        if not free_places:
            continue

        # make list with the new articles based on the free places
        free_places2, category_content = copy(free_places), []
        for article, date_published in articles:

            if article.id in category_fixed_content:
                continue

            # append in category_content to be reordered later
            category_content.append((free_places.pop(), date_published, article))

            if not len(free_places):
                break

        # sort new articles
        category_content.sort(key=operator.itemgetter(1), reverse=True)

        # update the content
        for i, ipos in enumerate(free_places2):

            try:
                old_pos, date_pub, art = category_content[i]

                if ipos:
                    if settings.DEBUG or dry_run:
                        print('DEBUG: update %s home position %d: %s' % (home.category, ipos, art))
                    if not dry_run:
                        home.set_article(art, ipos)
                else:
                    if settings.DEBUG or dry_run:
                        print('DEBUG: update %s home cover: %s' % (home.category, art))
                    if not dry_run:
                        home.set_article(art, 1)
            except IndexError:
                pass


class ArticleExtension(Model):
    SIZE_CHOICES = (
        ('R', u'Regular'),
        ('M', u'Mediano'),
        ('F', u'Full'),
    )
    article = ForeignKey(Article, verbose_name=u'artículo', related_name='extensions')
    headline = CharField(u'título', max_length=100, null=True, blank=True)
    body = TextField(u'cuerpo')
    size = CharField(u'size', max_length=1, choices=SIZE_CHOICES, default='R')
    background_color = CharField(u'background color', max_length=7, default='#eaeaea', null=True, blank=True)

    def __unicode__(self):
        return self.headline or u''

    def _is_published(self):
        return self.article.is_published
    is_published = property(_is_published)

    class Meta:
        ordering = ('article', 'headline')
        verbose_name = u'recuadro'
        verbose_name_plural = u'recuadros'


class ArticleBodyImage(Model):
    DISPLAY_CHOICES = (
        ('BG', u'Ancho regular'),
        ('MD', u'Ancho amplio'),
        ('FW', u'Ancho completo'),
    )
    article = ForeignKey(Article, verbose_name=u'artículo', related_name='body_image')
    image = ForeignKey(Photo, verbose_name=u'foto', related_name='photo')
    display = CharField(u'display', max_length=2, choices=DISPLAY_CHOICES, default='MD')

    def __unicode__(self):
        return (self.image.title or u'') if self.image else u''

    class Meta:
        verbose_name = u'imagen'
        verbose_name_plural = u'imagenes'


class PrintOnlyArticle(Model):
    headline = CharField(u'título', max_length=100)
    deck = CharField(u'bajada', max_length=255, blank=True, null=True)
    edition = ForeignKey(Edition, verbose_name=u'edición', related_name='print_only_articles')
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True)

    def __unicode__(self):
        return self.headline or u''

    class Meta:
        get_latest_by = 'date_created'
        ordering = ('id', )
        unique_together = ('headline', 'edition')
        verbose_name = u'artículo impreso'
        verbose_name_plural = u'artículos impresos'


class ArticleUrlHistory(Model):
    article = ForeignKey(Article)
    absolute_url = URLField(max_length=500, db_index=True)

    class Meta:
        unique_together = ('article', 'absolute_url')


class BreakingNewsModule(Model):
    is_published = BooleanField(u'publicado', default=False)
    headline = CharField(u'título', max_length=100)
    deck = CharField(u'bajada', max_length=255, blank=True, null=True)
    enable_notification = BooleanField(u'mostrar notificación de alerta', default=False)
    notification_url = URLField(u'URL destino de la notificación', blank=True, null=True)
    notification_text = CharField(u'texto de la notificación', max_length=255, blank=True, null=True)
    articles = ManyToManyField(Article, verbose_name=u'artículos relacionados', blank=True)
    embeds_headline = CharField(u'título de los incrustados', max_length=100, blank=True, null=True)
    embeds_description = CharField(u'descripción de los incrustados', max_length=255, blank=True, null=True)
    embed1_title = CharField(u'título de incrustado 1', max_length=100, blank=True, null=True)
    embed1_content = TextField(u'contenido de incrustado 1', blank=True, null=True)
    embed2_title = CharField(u'título de incrustado 2', max_length=100, blank=True, null=True)
    embed2_content = TextField(u'contenido de incrustado 2', blank=True, null=True)
    embed3_title = CharField(u'título de incrustado 3', max_length=100, blank=True, null=True)
    embed3_content = TextField(u'contenido de incrustado 3', blank=True, null=True)
    embed4_title = CharField(u'título de incrustado 4', max_length=100, blank=True, null=True)
    embed4_content = TextField(u'contenido de incrustado 4', blank=True, null=True)
    embed5_title = CharField(u'título de incrustado 5', max_length=100, blank=True, null=True)
    embed5_content = TextField(u'contenido de incrustado 5', blank=True, null=True)
    embed6_title = CharField(u'título de incrustado 6', max_length=100, blank=True, null=True)
    embed6_content = TextField(u'contenido de incrustado 6', blank=True, null=True)
    embed7_title = CharField(u'título de incrustado 7', max_length=100, blank=True, null=True)
    embed7_content = TextField(u'contenido de incrustado 7', blank=True, null=True)
    embed8_title = CharField(u'título de incrustado 8', max_length=100, blank=True, null=True)
    embed8_content = TextField(u'contenido de incrustado 8', blank=True, null=True)
    embed9_title = CharField(u'título de incrustado 9', max_length=100, blank=True, null=True)
    embed9_content = TextField(u'contenido de incrustado 9', blank=True, null=True)
    embed10_title = CharField(u'título de incrustado 10', max_length=100, blank=True, null=True)
    embed10_content = TextField(u'contenido de incrustado 10', blank=True, null=True)
    embed11_title = CharField(u'título de incrustado 11', max_length=100, blank=True, null=True)
    embed11_content = TextField(u'contenido de incrustado 11', blank=True, null=True)
    embed12_title = CharField(u'título de incrustado 12', max_length=100, blank=True, null=True)
    embed12_content = TextField(u'contenido de incrustado 12', blank=True, null=True)
    embed13_title = CharField(u'título de incrustado 13', max_length=100, blank=True, null=True)
    embed13_content = TextField(u'contenido de incrustado 13', blank=True, null=True)
    embed14_title = CharField(u'título de incrustado 14', max_length=100, blank=True, null=True)
    embed14_content = TextField(u'contenido de incrustado 14', blank=True, null=True)
    publications = ManyToManyField(Publication, verbose_name=u'portada de publicaciones', blank=True)
    categories = ManyToManyField(Category, verbose_name=u'portada de áreas', blank=True)

    def __unicode__(self):
        return self.headline or u''

    def covers(self):
        return u', '.join(
            [p.__unicode__() for p in self.publications.all()] + [c.__unicode__() for c in self.categories.all()]
        )
    covers.short_description = u'portadas'

    def has_embed(self, i):
        return getattr(self, 'embed%d_title' % i) or getattr(self, 'embed%d_content' % i)

    def has_embeds(self, i, j):
        return self.has_embed(i) or self.has_embed(j)

    def has_embed2(self):
        return self.has_embed(2)

    def has_embed4(self):
        return self.has_embed(4)

    def has_embed6(self):
        return self.has_embed(6)

    def has_embed8(self):
        return self.has_embed(8)

    def has_embed10(self):
        return self.has_embed(10)

    def has_embed12(self):
        return self.has_embed(12)

    def has_embed14(self):
        return self.has_embed(14)

    def has_embeds12(self):
        return self.has_embeds(1, 2)

    def has_embeds34(self):
        return self.has_embeds(3, 4)

    def has_embeds56(self):
        return self.has_embeds(5, 6)

    def has_embeds78(self):
        return self.has_embeds(7, 8)

    def has_embeds910(self):
        return self.has_embeds(9, 10)

    def has_embeds1112(self):
        return self.has_embeds(11, 12)

    def has_embeds1314(self):
        return self.has_embeds(13, 14)

    class Meta:
        verbose_name = u'módulo de último momento'
        verbose_name_plural = u'módulos de último momento'


def get_publishing_datetime():
    today = date.today()
    publishing_hour, publishing_minute = [int(i) for i in settings.PUBLISHING_TIME.split(':')]
    return datetime(
        today.year, today.month, today.day, publishing_hour, publishing_minute)


def get_published_date():
    now = datetime.now()
    publishing = get_publishing_datetime()
    publishing_date = date(publishing.year, publishing.month, publishing.day)
    if now > publishing:
        return publishing_date
    return publishing_date - timedelta(1)


def get_current_edition(publication=None):
    """
    Return last edition of publication if given, or the publications using root url as their home page if the
    publication slug is not given.
    """
    today, now, filters = date.today(), datetime.now(), {}
    publishing_hour, publishing_minute = [int(i) for i in settings.PUBLISHING_TIME.split(':')]
    publishing = datetime(today.year, today.month, today.day, publishing_hour, publishing_minute)

    if publication:
        filters['publication'] = publication.id
    else:
        filters['publication__in'] = [
            p.id for p in Publication.objects.filter(slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL)
        ]

    filters['date_published__lt' + ('e' if now > publishing else '')] = today
    try:
        return Edition.objects.filter(**filters).latest()
    except Exception as e:
        if settings.DEBUG:
            print(u"ERROR: %s" % e)
        return None


def get_latest_edition(publication=None):
    if not publication:
        publication = get_object_or_404(Publication, slug=settings.DEFAULT_PUB)
    return publication.latest_edition()


def get_current_feeds():
    """
    NOTE: if no current_edition found, next editions are taken using "today" as date contition.
    """
    # editions for "root" publications (current and "next")
    current_edition = get_current_edition()
    next_editions = Edition.objects.filter(
        publication__public=True,
        publication__slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL,
        date_published__gt=current_edition.date_published if current_edition else date.today(),
    ).order_by('date_published')
    editions_ids = ([str(current_edition.id)] if current_edition else []) + (
        [str(next_editions[0].id)] if next_editions else []
    )

    # editions for all the other publications (current and "next")
    for p in Publication.objects.filter(public=True).exclude(slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL):
        current_edition = get_current_edition(p)
        next_editions = Edition.objects.filter(
            publication=p, date_published__gt=current_edition.date_published if current_edition else date.today()
        ).order_by('date_published')
        editions_ids += ([str(current_edition.id)] if current_edition else []) + (
            [str(next_editions[0].id)] if next_editions else []
        )

    return Article.objects.filter(is_published=True).extra(
        where=[
            'core_article.id=core_articlerel.article_id',
            'core_articlerel.edition_id IN (%s)' % ','.join(editions_ids),
        ],
        tables=['core_articlerel'],
    ).distinct()
