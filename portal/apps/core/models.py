# -*- coding: utf-8 -*-
from past.utils import old_div
from os.path import basename, splitext, dirname, join, isfile
import locale
import tempfile
import operator
import json
from collections import OrderedDict
from requests.exceptions import ConnectionError
from kombu.exceptions import OperationalError as KombuOperationalError
from sorl.thumbnail import get_thumbnail
from PIL import Image
from bs4 import BeautifulSoup
import readtime
import mutagen
import w3storage
from martor.models import MartorField

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.http import HttpResponse, Http404
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sitemaps import ping_google
from django.db import IntegrityError, connection
from django.db.models import (
    Q,
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
    JSONField,
    Index,
    SET_NULL,
    CASCADE,
)
from django.db.models.signals import post_save
from django.db.utils import OperationalError
from django.template import Engine, Context
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils.timezone import datetime, timedelta, make_aware, now, template_localtime
from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.utils.html import escape

from apps import blocklisted
from photologue_ladiaria.models import PhotoExtended
from photologue.models import Gallery, Photo
from audiologue.models import Audio
from tagging.fields import TagField
from tagging.models import Tag
import thedaily
from videologue.models import Video, YouTubeVideo

from .managers import get_published_kwargs, PublishedArticleManager, EditionManager, SlugNaturalManager
from .templatetags.ldml import ldmarkup, amp_ldmarkup, cleanhtml, remove_markup
from .utils import (
    datetime_isoformat,
    get_pdf_pdf_upload_to,
    get_pdf_cover_upload_to,
    CT,
    smart_quotes,
    update_article_url_in_coral_talk,
    get_category_template,
)


def remove_media_root(path):
    return path.replace(settings.MEDIA_ROOT, '')


class Publication(Model):
    objects = SlugNaturalManager()
    name = CharField('nombre', max_length=100)
    twitter_username = CharField(
        'Nombre de usuario de Twitter',
        max_length=15,
        blank=True,
        null=True,
        help_text='Nombre de usuario de Twitter que se menciona cuando artículos de esta publicación son compartidos '
        'en Twitter (escribir sin @)',
    )
    description = TextField('descripción', null=True, blank=True, help_text='Se muestra en el componente de portada.')
    slug = SlugField('slug', unique=True)
    headline = CharField('título', max_length=100)
    weight = PositiveSmallIntegerField('orden', default=0)
    public = BooleanField('público', default=True)
    has_newsletter = BooleanField('tiene NL', default=False)
    newsletter_new_pill = BooleanField('pill de "nuevo" para la newsletter en el perfil de usuario', default=False)
    newsletter_name = CharField(max_length=64, blank=True, null=True)
    newsletter_tagline = CharField(max_length=128, blank=True, null=True)
    newsletter_periodicity = CharField(max_length=64, blank=True, null=True)
    newsletter_header_color = CharField('color de cabezal para NL', max_length=7, default='#262626')
    newsletter_campaign = CharField(max_length=64, blank=True, null=True)
    newsletter_automatic_subject = BooleanField(default=True)
    newsletter_subject = CharField('asunto', max_length=256, blank=True, null=True)
    newsletter_logo = ImageField('logo para NL', upload_to='publications', blank=True, null=True)
    extra_context = JSONField(
        "Contexto extra para portadas y newsletter",
        default=dict,
        help_text=mark_safe(
            'Diccionario Python en formato JSON que se utilizará como contexto al inicio de la construcción del '
            'contexto predeterminado, sus entradas, si hay colisión, serían sobreescritas por la vista de portada en '
            'backend o comando de envío de newsletter.<br>'
            'Ejemplo: <code>{"custom_footer_msg": "Esta newsletter fue generada utilizando utopia-cms"}</code>'
        ),
    )
    subscribe_box_question = CharField(max_length=64, blank=True, null=True)
    subscribe_box_nl_subscribe_auth = CharField(max_length=128, blank=True, null=True)
    subscribe_box_nl_subscribe_anon = CharField(max_length=128, blank=True, null=True)
    image = ImageField('logo', upload_to='publications', blank=True, null=True)
    full_width_cover_image = ForeignKey(
        Photo, on_delete=CASCADE, verbose_name='foto full de portada', blank=True, null=True
    )
    is_emergente = BooleanField('es emergente', default=False)
    new_pill = BooleanField('pill de "nuevo" en el componente de portada', default=False)
    html_title = CharField(
        "contenido del tag <title> y del metadato 'og:title' del código HTML",
        max_length=128,
        blank=True,
        null=True,
    )
    meta_description = CharField(
        "contenido del metadato 'description' y 'og:description' del código HTML",
        max_length=256,
        blank=True,
        null=True,
    )
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

    __original_slug = None  # needed for articles url update on save

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        # needed for articles url update on save
        super().__init__(*args, **kwargs)
        self.__original_slug = self.slug

    def save(self, *args, **kwargs):
        # needed for articles url update
        super().save(*args, **kwargs)
        if getattr(settings, "CORE_PUBLICATIONS_PERMS_UPDATE", True):
            # also permission creation for insert or update on save (see github issue 29)
            try:
                Permission.objects.update_or_create(
                    codename="es_suscriptor_" + self.__original_slug,
                    defaults={
                        "name": "Es suscriptor " + ("actualmente" if self.slug == settings.DEFAULT_PUB else self.name),
                        "content_type": ContentType.objects.get_for_model(thedaily.models.Subscriber),
                        "codename": "es_suscriptor_" + self.slug,
                    },
                )
            except IntegrityError:
                pass
        if self.__original_slug != self.slug:
            try:
                from .tasks import update_article_urls
                update_article_urls.delay(self.slug)
            except KombuOperationalError as oe_exc:
                if settings.DEBUG:
                    print("ERROR: update_article_urls could not be started (%s)" % oe_exc)
        self.__original_slug = self.slug

    def get_absolute_url(self):
        return reverse(
            'home', kwargs={} if self.slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL else {'domain_slug': self.slug}
        )

    @staticmethod
    def multi():
        return Publication.objects.count() > 1

    def newsletter_preview_url(self):
        """
        Returns the url for the NL staff-allowed preview
        """
        try:
            # allow a custom-by-slug override url pattern defined by a third-party module
            result = reverse("publication-%s-nl-preview" % self.slug)
        except NoReverseMatch:
            try:
                # TODO: not yet opensourced (we have a privative version that should be opensourced asap)
                result = reverse("publication-nl-preview", kwargs={"publication_slug": self.slug})
            except NoReverseMatch:
                result = None
        return result

    def profile_newsletter_name(self):
        """
        Returns the newsletter name to show in the edit profile view
        """
        if self.slug in getattr(settings, "THEDAILY_EDIT_PROFILE_PUBLICATIONS_NL_USE_NAMEONLY", []):
            return self.name
        else:
            return self.newsletter_name or self.name

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
                self.subscriber_set.filter(user__is_active=True)
                .exclude(user__email='')
                .values_list('user__email', flat=True)
            )
            - blocklisted
        )

    subscriber_count.short_description = 'Suscrip. NL'

    def image_tag(self):
        url = None
        if self.image:
            logo_filename = self.image.path
            try:
                logo_image = Image.open(logo_filename)
            except IOError:
                logo_image = None
            if logo_image and logo_image.size[0] > 120:
                tmpfile, f = tempfile.mkstemp('.png', dir=settings.MEDIA_ROOT)
                logo_image.convert('RGB').save(f, optimize=True)
                url = get_thumbnail(f, '120', crop='center', quality=99).url
            else:
                url = '%s%s' % (settings.MEDIA_URL, self.image)
        return mark_safe(
            '<a href="/admin/core/publication/%d/"><img src="%s" style="background:%s;"/></a>' % (
                self.id, url, self.newsletter_header_color
            )
        ) if url else ''

    image_tag.short_description = 'logo'

    def get_full_width_cover_image_tag(self):
        return mark_safe(
            '<a href="/admin/core/publication/%d/"><img src="%s" alt="%s"></a>' % (
                self.id, self.full_width_cover_image.get_admin_thumbnail_url(), self.full_width_cover_image
            )
        ) if self.full_width_cover_image else ''

    get_full_width_cover_image_tag.short_description = 'foto full de portada'

    def natural_key(self):
        return (self.slug,)

    class Meta:
        ordering = ['weight']
        verbose_name = 'publicación'
        verbose_name_plural = 'publicaciones'


class PortableDocumentFormatBaseModel(Model):
    pdf = FileField(
        'archivo PDF',
        max_length=150,
        upload_to=get_pdf_pdf_upload_to,
        blank=True,
        null=True,
        help_text='<strong>AVISO:</strong> Si es mayor a 8MB probablemente no se pueda enviar por mail.',
    )
    pdf_md5 = CharField('checksum', max_length=32, editable=False)
    downloads = PositiveIntegerField('descargas', default=0)
    cover = ImageField('tapa', upload_to=get_pdf_cover_upload_to, blank=True, null=True)
    date_published = DateField('fecha de publicación', default=now, db_index=True)
    date_created = DateTimeField('fecha de creación', auto_now_add=True)

    def __str__(self):
        return self.pdf[self.pdf.rfind('/') + 1:]

    class Meta:
        abstract = True
        get_latest_by = 'date_published'
        ordering = ('-date_published',)

    def get_pdf_filename(self):
        return None

    def get_cover_filename(self):
        return '%s.jpg' % self.get_pdf_filename()[:-4]

    def get_download_url(self):
        return reverse(
            'edition_download',
            kwargs={
                'publication_slug': self.publication.slug,
                'year': self.date_published.year,
                'month': '%02d' % self.date_published.month,
                'day': '%02d' % self.date_published.day,
                'filename': basename(self.pdf.path),
            },
        )

    def download(self, request=None):
        try:
            response = HttpResponse(self.pdf, content_type='application/pdf')
        except IOError:
            raise Http404
        else:
            response['Content-Disposition'] = 'attachment; filename=%s' % basename(self.pdf.path)
            return response

    def date_published_verbose(self, short=True):
        locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)
        result = (
            (
                "{d:%a}. {d.day} {d:%b}."
                if now().date().year == self.date_published.year else "{d.day} {d:%b, %Y}"
            ) if short else "{d:%A} {d.day} de {d:%B de %Y}"
        ).format(d=self.date_published)
        return result.title() if short else result.capitalize()


""" TODO: better enable this after new structure works well (**) (why? what does it improve?)
class EditionSection(models.Model):
    edition = ForeignKey(Edition)
    section = ForeignKey(Section)
    home_order = PositiveSmallIntegerField('orden en Portada', default=0)
    in_home = BooleanField('mostrar_en_portada', default=True)
    style = CharField('estilo', max_length=2, choices=STYLE_CHOICES, blank=True, null=True)
"""


class Edition(PortableDocumentFormatBaseModel):
    """
    A publication's edition.
    """
    objects = EditionManager()
    title = TextField('título', null=True)
    publication = ForeignKey(
        Publication, on_delete=CASCADE, verbose_name='publicación', related_name="%(app_label)s_%(class)s"
    )
    # (**) sections = ManyToManyField(Section, through='EditionSection')

    class Meta(PortableDocumentFormatBaseModel.Meta):
        verbose_name = 'edición'
        verbose_name_plural = 'ediciones'
        unique_together = [["date_published", "publication"]]  # TODO: is this the right way? why not a single tuple?

    def __str__(self):
        try:
            display_name = '%s - %s' % (self.date_published.strftime('%d-%m-%Y'), self.publication.name)
        except Exception:
            display_name = self.date_published.strftime('%d-%m-%Y')
        return display_name

    def edition_pub(self):
        return str(self)

    def natural_key(self):
        return (self.date_published,) + self.publication.natural_key()
    natural_key.dependencies = ['core.publication']

    edition_pub.short_description = 'Fecha publicada'

    def get_supplements(self):
        return self.supplements.values_list('pdf', 'cover') or ''

    get_supplements.short_description = 'suplementos'

    def get_absolute_url(self):
        reverse_kwargs = {
            'year': self.date_published.year,
            'month': self.date_published.month,
            'day': self.date_published.day,
        }
        if self.publication and self.publication.slug not in settings.CORE_PUBLICATIONS_USE_ROOT_URL:
            reverse_kwargs['publication_slug'] = self.publication.slug
        return reverse('edition_detail', kwargs=reverse_kwargs)

    def published_articles(self):
        return (
            Article.published.extra(
                where=['core_article.id=core_articlerel.article_id', 'core_articlerel.edition_id=%d' % self.id],
                tables=['core_articlerel'],
            )
            .order_by('articlerel__top_position')
            .distinct()
        )

    def newsletter_featured_articles(self):
        return self.published_articles().filter(newsletter_featured=True)

    def get_pdf_filename(self):
        return '%s-%s.pdf' % (self.publication.slug, self.date_published.strftime('%Y%m%d'))

    def cover_image_file_exists(self):
        try:
            result = self.cover and bool(self.cover.file)
        except IOError:
            result = False
        return result

    @property
    def top_articles(self):
        try:
            return list(
                OrderedDict.fromkeys(
                    [
                        ar.article
                        for ar in self.articlerel_set.prefetch_related(
                            'article__main_section__edition__publication',
                            'article__main_section__section',
                            'article__photo__extended__photographer',
                            'article__byline',
                        )
                        .filter(article__is_published=True, home_top=True)
                        .order_by('top_position')
                    ]
                )
            )
        except OperationalError:
            return []

    def get_articles_in_section(self, section):
        return list(
            OrderedDict.fromkeys(
                [
                    ar.article
                    for ar in self.articlerel_set.prefetch_related(
                        'article__main_section__edition__publication',
                        'article__main_section__section',
                        'article__photo__extended__photographer',
                        'article__byline',
                    )
                    .filter(article__is_published=True, section=section)
                    .order_by('position')
                ]
            )
        )

    def previous_section(self, section):
        editions = [
            ar.edition for ar in ArticleRel.objects.filter(
                section=section, edition__date_published__lt=self.date_published
            ).order_by('-edition__date_published')
        ]
        return editions[0] if editions else None

    @property
    def previous_edition(self):
        try:
            return Edition.objects.filter(date_published__lt=self.date_published).order_by('-date_published')[0]
        except Exception:
            return None

    @property
    def next_edition(self):
        try:
            return Edition.objects.filter(
                date_published__gt=self.date_published, date_published__lte=now().date()
            ).order_by('date_published')[0]
        except Exception:
            return None

    def nl_serialize(self):
        result = {
            'publication': {
                'newsletter_header_color': self.publication.newsletter_header_color,
                'newsletter_campaign': self.publication.newsletter_campaign,
                'get_absolute_url': self.publication.get_absolute_url(),
            },
            'pdf': {'path': self.pdf.path} if self.pdf else None,
            'date_published': self.date_published_verbose(False),
            'supplements': [s.pdf.path for s in Supplement.objects.filter(date_published=self.date_published)],
        }
        if self.publication.slug in getattr(settings, 'CORE_PUBLICATIONS_EDITION_DOWNLOAD', ()):
            result['download_url'] = self.get_download_url()
        return result


class EditionHeader(Model):
    edition = OneToOneField(Edition, on_delete=CASCADE, verbose_name='edición')
    title = CharField('título', max_length=127)
    subtitle = CharField('subtítulo', max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = 'encabezado de edición'
        verbose_name_plural = 'encabezados de edición'

    def __str__(self):
        return '%s - %s' % (self.edition, self.title)


class Supplement(PortableDocumentFormatBaseModel):
    edition = ForeignKey(Edition, on_delete=CASCADE, verbose_name='edición', related_name='supplements')
    name = CharField('nombre', max_length=2, choices=settings.CORE_SUPPLEMENT_NAME_CHOICES)
    slug = SlugField('slug', unique=True)
    headline = CharField('titular', max_length=100)
    public = BooleanField('público', default=True)

    class Meta:
        get_latest_by = 'date_published'
        ordering = ('-date_published', 'name')
        unique_together = ('date_published', 'name')
        verbose_name = 'suplemento'
        verbose_name_plural = 'suplementos'

    def __str__(self):
        return '%s - %s' % (self.date_published.strftime('%d-%m-%Y'), self.get_name_display())

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

    def get_absolute_url(self):
        return reverse(
            'supplement_detail',
            kwargs={
                'supplement_slug': self.slug,
                'year': self.date_published.year,
                'month': self.date_published.month,
                'day': self.date_published.day,
            },
        )

    def get_pdf_filename(self):
        return '%s-%s-%s.pdf' % (
            self.edition.get_name_display().replace(' ', '_'),
            self.date_published.strftime('%Y%m%d'),
            self.slug.replace('-', '_'),
        )

    def get_pdf_url(self):
        try:
            return self.pdf.url
        except Exception:
            return ""


class Category(Model):
    objects = SlugNaturalManager()
    name = CharField('nombre', max_length=50, unique=True)
    slug = SlugField('slug', blank=True, null=True)
    description = TextField('descripción', blank=True, null=True)
    order = PositiveSmallIntegerField('orden', blank=True, null=True)
    has_newsletter = BooleanField('tiene NL', default=False)
    newsletter_new_pill = BooleanField('pill de "nuevo" para la newsletter en el perfil de usuario', default=False)
    newsletter_tagline = CharField(max_length=128, blank=True, null=True)
    newsletter_periodicity = CharField(max_length=64, blank=True, null=True)
    newsletter_from_name = CharField("nombre en el 'From' del mensaje", max_length=64, blank=True, null=True)
    newsletter_from_email = EmailField("email en el 'From' del mensaje", blank=True, null=True)
    newsletter_automatic_subject = BooleanField(default=True)
    newsletter_subject = CharField('asunto', max_length=256, blank=True, null=True)
    newsletter_extra_context = JSONField(
        "Contexto extra para newsletter",
        default=dict,
        help_text=mark_safe(
            'Diccionario Python en formato JSON que se utilizará como contexto al inicio de la construcción del '
            'contexto predeterminado, sus entradas, si hay colisión, serían sobreescritas por el comando de envío.<br>'
            'Ejemplo: <code>{"custom_footer_msg": "Esta newsletter fue generada utilizando utopia-cms"}</code>'
        ),
    )
    subscribe_box_question = CharField(max_length=64, blank=True, null=True)
    subscribe_box_nl_subscribe_auth = CharField(max_length=128, blank=True, null=True)
    subscribe_box_nl_subscribe_anon = CharField(max_length=128, blank=True, null=True)
    title = CharField('título en el componente de portada', max_length=50, blank=True, null=True)
    more_link_title = CharField(
        'texto en el link "más" del componente de portada', max_length=50, blank=True, null=True
    )
    new_pill = BooleanField('pill de "nuevo" en el componente de portada y menú', default=False)
    full_width_cover_image = ForeignKey(
        Photo, on_delete=CASCADE, verbose_name='foto full de portada', blank=True, null=True
    )
    full_width_cover_image_title = CharField(
        'título para foto full',
        max_length=50,
        null=True,
        blank=True,
        help_text='Se muestra sólo si la foto está seteada. (Máx 50 caract.)',
    )
    full_width_cover_image_lead = TextField(
        'bajada para foto full',
        null=True,
        blank=True,
        help_text='Se muestra sólo si la foto y el título están seteados.',
    )
    exclude_from_top_menu = BooleanField('Excluir ítem en menú superior de escritorio', default=False)
    dropdown_menu = BooleanField(
        'Usar menú desplegable en menú superior de escritorio con las secciones del área',
        default=False,
    )
    html_title = CharField(
        "contenido del tag <title> y del metadato 'og:title' del código HTML",
        max_length=128,
        blank=True,
        null=True,
    )
    meta_description = CharField(
        "contenido del metadato 'description' y 'og:description' del código HTML",
        max_length=256,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name

    def latest_articles(self, exclude=[]):
        return list(self.home.articles.exclude(id__in=exclude)) if hasattr(self, 'home') else []

    def articles(self):
        """
        Returns all articles published on this category
        """
        return Article.objects.filter(
            id__in=[
                a.id
                for a in Article.objects.raw(
                    """
                    SELECT DISTINCT core_article.id
                    FROM core_article
                    JOIN core_articlerel ON
                        core_article.id = core_articlerel.article_id
                    JOIN core_section ON
                        core_articlerel.section_id = core_section.id
                    JOIN core_edition ON
                        core_articlerel.edition_id = core_edition.id
                    WHERE core_section.category_id = %d
                        AND is_published AND core_edition.date_published <= CURRENT_DATE
                    ORDER BY core_article.date_published DESC
                    """
                    % self.id
                )
            ]
        )

    def articles_count(self, max=None, exclude_sections=[], debug=False):
        """
        Returns the number of articles published in this category.
        If max is given, the result will be allways less or equal this max value.
        """
        with connection.cursor() as cursor:
            subquery_part = (
                """
                FROM core_article
                JOIN core_articlerel ON
                    core_article.id = core_articlerel.article_id
                JOIN core_section ON
                    core_articlerel.section_id = core_section.id
                JOIN core_edition ON
                    core_articlerel.edition_id = core_edition.id
                WHERE core_section.category_id = %d AND is_published AND core_edition.date_published <= CURRENT_DATE
            """
                % self.id
            )
            if exclude_sections:
                subquery_part += "AND core_section.slug NOT IN (%s)" % ",".join("'%s'" % s for s in exclude_sections)
            if max:
                query = "SELECT COUNT(*) FROM (SELECT DISTINCT core_article.id %s LIMIT %d) final" % (
                    subquery_part,
                    max,
                )
            else:
                query = "SELECT COUNT(DISTINCT core_article.id) " + subquery_part
            if debug:
                print(query)
            cursor.execute(query)
            return cursor.fetchone()[0]

    def subscriber_count(self):
        return len(
            set(
                self.subscriber_set.filter(user__is_active=True)
                .exclude(user__email='')
                .values_list('user__email', flat=True)
            )
            - blocklisted
        )

    subscriber_count.short_description = 'Suscrip. NL'

    def get_full_width_cover_image_tag(self):
        return mark_safe(
            '<a href="/admin/core/category/%d/"><img src="%s" alt="%s"></a>' % (
                self.id, self.full_width_cover_image.get_admin_thumbnail_url(), self.full_width_cover_image
            )
        ) if self.full_width_cover_image else ''

    get_full_width_cover_image_tag.short_description = 'foto full de portada'

    def get_absolute_url(self):
        return reverse('home', kwargs={'domain_slug': self.slug})

    def newsletter_preview_url(self):
        """
        Returns the url for the NL staff-allowed preview
        """
        try:
            # allow a custom-by-slug override url pattern defined by a third-party module
            result = reverse("category-%s-nl-preview" % self.slug)
        except NoReverseMatch:
            try:
                result = reverse("category-nl-preview", kwargs={"slug": self.slug})
            except NoReverseMatch:
                result = None
        return result

    def profile_newsletter_name(self):
        """
        Returns the newsletter name to show in the edit profile view
        TODO: instead of use a setting to customize (due an urgent req), this should be done like in Pubs, using a
              new field "newsletter_name", this needs some time-work to propagate the impact of adding this new field,
              because, for ex. nl subject should also use it prior to object name, etc.
        """
        if self.slug in getattr(settings, "THEDAILY_EDIT_PROFILE_CATEGORY_NL_USE_FROM_NAME", []):
            return self.newsletter_from_name
        else:
            return self.name

    def nl_featured_section_articles(self):
        """
        Returns a list containg the articles matching the 3 values that can be defined in the related setting.
        Examples:
        1. if settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS == {"this_category_slug": ("some_section", 1, 2)}
            then, this method will return the 2 most recent articles within 1 day published in "some_section" section.
        2. The third element of the tuple can be omitted and defaulted to 1:
            if settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS == {"this_category_slug": ("some_section", 7)}
            then, this method will return the latest article within last 7 days published in "some_section" section.
        """
        settings_tuple = getattr(settings, "CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS", {}).get(self.slug, ())
        st_len, featured_section, days_ago, take_count = len(settings_tuple), None, None, None
        result = Article.published.none()
        if st_len:
            if st_len == 3:
                featured_section, days_ago, take_count = settings_tuple
            elif st_len == 2:
                (featured_section, days_ago), take_count = settings_tuple, 1
            if all((featured_section, days_ago, take_count)):
                try:
                    result = self.section_set.get(
                        slug=featured_section
                    ).published_articles(date_published__gte=now() - timedelta(days_ago))[:take_count]
                except Section.DoesNotExist:
                    pass
        return result

    def natural_key(self):
        return (self.slug,)

    class Meta:
        verbose_name = 'área'
        ordering = ('order', 'name')


class Section(Model):
    objects = SlugNaturalManager()

    SECTION_1 = '1'
    SECTION_2 = '2'
    SECTION_3 = '3'

    category = ForeignKey(Category, on_delete=CASCADE, verbose_name='área', blank=True, null=True)
    name = CharField('nombre', max_length=50, unique=True)
    included_in_category_menu = BooleanField("incluída en el menú del área", default=True)
    name_in_category_menu = CharField('nombre en el menú del área', max_length=50, blank=True, null=True)
    slug = SlugField('slug', unique=True)
    description = TextField('descripción', blank=True, null=True)
    contact = EmailField("email", blank=True, null=True)
    date_created = DateTimeField('fecha de creación', auto_now_add=True)
    home_order = PositiveSmallIntegerField('orden', default=0)
    in_home = BooleanField(
        'en portada',
        default=False,
        help_text='si el componente de portadas de esta categoría está insertado, esta opción lo muestra u oculta.',
    )
    imagen = ImageField('imagen o ilustración', upload_to='section_images', blank=True, null=True)
    publications = ManyToManyField(Publication, verbose_name='publicaciones', blank=True)
    home_block_all_pubs = BooleanField(
        'usar todas las publicaciones en módulos de portada',
        default=True,
        help_text='Marque esta opción para mostrar artículos de todas las publicaciones en los módulos de portada.',
    )
    home_block_show_featured = BooleanField(
        'mostrar artículos destacados en módulos de portada',
        default=True,
        help_text='Marque esta opción para mostrar artículos destacados en los módulos de portada.',
    )
    background_color = CharField('background color', max_length=7, default='#ffffff')
    white_text = BooleanField('texto blanco', default=False)
    show_description = BooleanField('mostrar descripción', default=False)
    show_image = BooleanField('mostrar imagen', default=False)
    html_title = CharField(
        "contenido del tag <title> y del metadato 'og:title' del código HTML",
        max_length=128,
        blank=True,
        null=True,
    )
    meta_description = CharField(
        "contenido del metadato 'description' y 'og:description' del código HTML",
        max_length=256,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name

    def nl_display_name(self):
        """
        This method allows to include the "hierarchy" for those categories that allow that feature by settings for the
        purpose to be rendered in newsletters cards, where calling the aticle hierarchy template tag will not be a good
        approach.
        """
        if self.category:
            allowed = getattr(settings, "CORE_CATEGORY_ALLOW_RENDER_HIERARCHY", ())
            if allowed and self.category.slug in allowed:
                return '&nbsp;›&nbsp;'.join([str(self.category), str(self)])
        return str(self)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Section, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('section_detail', kwargs={'section_slug': self.slug})

    def is_satirical(self):
        return self.slug in getattr(settings, 'CORE_SATIRICAL_SECTIONS', ())

    def get_publications(self):
        return ', '.join(self.publications.values_list('name', flat=True))

    get_publications.short_description = 'publicaciones'

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
        TODO: SQL generation shuld be according with ..utils.get_section_articles_sql
        """
        extra_where, extra_join = '', ''

        if not all_sections:
            extra_where = ' AND core_articlerel.section_id=%s' % self.id

        if article_type:
            extra_where += " AND core_article.type='%s'" % article_type

        if exclude_articles_ids:
            extra_where += ' AND core_article.id NOT IN (%s)' % ','.join([str(x) for x in exclude_articles_ids])

        if publications_ids:
            extra_join += ' JOIN core_edition ON core_articlerel.edition_id = core_edition.id'
            extra_where += ' AND core_edition.publication_id IN (%s)' % ','.join([str(x) for x in publications_ids])

        query = """
            SELECT core_article.id
            FROM core_article
                JOIN core_articlerel ON core_article.id = core_articlerel.article_id%s
            WHERE is_published%s
            GROUP BY id
            ORDER BY core_article.date_published DESC
            LIMIT %s
        """ % (
            extra_join,
            extra_where,
            limit,
        )

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
        return Article.objects.raw(
            """
            SELECT core_article.*
            FROM core_article JOIN core_articlerel
                ON core_article.id = core_articlerel.article_id
            WHERE core_articlerel.section_id=%s AND is_published
                AND allow_related AND core_article.id!=%s
            GROUP BY id ORDER BY date_published DESC
            LIMIT 4"""
            % (self.id, exclude_id)
        )

    def latest4relatedbycategory(self, category, exclude_id):
        """
        devuelve los últimos 4 articulos de la categoría que acepten ser
        relacionados excluyendo al que se le pasa por parametro.
        """
        return Article.objects.raw(
            """
            SELECT core_article.*
            FROM core_article JOIN core_articlerel
                ON core_article.id = core_articlerel.article_id
                JOIN core_section
                ON core_articlerel.section_id = core_section.id
            WHERE is_published AND allow_related
                AND core_section.category_id=%s AND core_article.id!=%s
            GROUP BY id ORDER BY date_published DESC
            LIMIT 4"""
            % (category, exclude_id)
        )

    def latest4relatedbypublication(self, publication, exclude_id):
        """
        devuelve los últimos 4 articulos de la publicacion que acepten ser
        relacionados excluyendo al que se le pasa por parametro.
        """
        return (
            Article.objects.raw(
                """
            SELECT a.* FROM core_article a JOIN core_articlerel ar ON a.id=ar.article_id
                JOIN core_edition e ON ar.edition_id=e.id
            WHERE a.is_published AND a.allow_related AND e.publication_id=%s AND a.id!=%s
            GROUP BY a.id ORDER BY a.date_published DESC LIMIT 4"""
                % (publication, exclude_id)
            )
            if settings.CORE_ENABLE_RELATED_ARTICLES
            else []
        )

    def latest_article(self):
        """
        Returns the latest article (by article's date_published) published in this section.
        TODO: This method is called from send_category_nl.py, section.py and category.py and all this calls can raise
              IndexError if this method returns an empty list.
        """
        latest_qs = self.articlerel_set.filter(article__is_published=True).order_by('-article__date_published')
        return [latest_qs[0].article] if latest_qs.exists() else []

    def mas_vistos(self):
        desde = now() - timedelta(days=60)
        return Article.objects.filter(sections__id=self.id, date_published__gt=desde).order_by('views')[:10]

    def published_articles(self, **filter_kwargs):
        """
        Returns all this section's published articles supporting filtering by keyword args
        """
        return self.articles_core.filter(is_published=True, **filter_kwargs).distinct()

    def latest_articles(self):
        """
        Returns this section's articles in the last 24 hours (or 48 on sundays)
        """
        return self.articles_core.filter(
            is_published=True,
            date_published__gt=now() - timedelta(2 if now().date().isoweekday() < 7 else 3),
        ).distinct()

    def articles_count(self):
        return self.articles_core.count()

    articles_count.short_description = '# Artículos'

    def natural_key(self):
        return (self.slug,)

    class Meta:
        get_latest_by = 'date_created'
        ordering = ('home_order', 'name', 'date_created')
        verbose_name = 'sección'
        verbose_name_plural = 'secciones'


class Journalist(Model):
    objects = SlugNaturalManager()

    JOB_CHOICES = (
        ('PE', 'Periodista'),
        ('CO', 'Columnista'),
    )
    DEFAULT_SOCIAL_ORDER = ['facebook', 'twitter', 'google plus', 'instagram',
                            'mastodon', 'threads', 'youtube', 'linkedin', 'tiktok'
                            'bluesky', 'trumblr', 'twitch', 'otro 1', 'otro 2', 'otro 3']

    name = CharField('nombre', max_length=50, unique=True)
    email = EmailField(blank=True, null=True)
    slug = SlugField('slug', unique=True)
    image = ImageField('imagen', upload_to='journalist', blank=True, null=True)
    job = CharField(
        'trabajo',
        max_length=2,
        choices=JOB_CHOICES,
        default='PE',
        help_text='Rol en que se desempeña principalmente.',
    )
    bio = TextField('bio', null=True, blank=True, help_text='Bio aprox 200 caracteres.')
    sections = ManyToManyField(Section, verbose_name='secciones', blank=True)
    fb = URLField('facebook', blank=True, null=True)
    tt = URLField('X', blank=True, null=True)
    ig = URLField('instagram', blank=True, null=True)
    mtdn = URLField('mastodon', blank=True, null=True)
    thds = URLField('threads', blank=True, null=True)
    ytb = URLField('youtube', blank=True, null=True)
    lnkin = URLField('linkedin', blank=True, null=True)
    tktk = URLField('tiktok', blank=True, null=True)
    bs = URLField('bluesky', blank=True, null=True)
    tr = URLField('trumblr', blank=True, null=True)
    tw = URLField('twitch', blank=True, null=True)
    other_one = URLField('otro 1', blank=True, null=True)
    other_two = URLField('otro 2', blank=True, null=True)
    other_three = URLField('otro 3', blank=True, null=True)

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.slug,)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Journalist, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            'journalist_detail',
            kwargs={'journalist_job': self.get_job_display().lower(), 'journalist_slug': self.slug},
        )

    def get_sections(self):
        return self.sections.all()

    def image_file_exists(self):
        try:
            result = self.image and bool(self.image.file)
        except IOError:
            result = False
        return result

    def get_socials(self):
        """
        Get all socials that has value
        @return field_value: social fields with values in dict format
        {"field_verbose_name": "field_value"}
        """
        custom_order = getattr(settings, "CORE_JOURNALIST_SOCIAL_ORDER", None)
        if custom_order:
            verbose_names_of_interest = custom_order
        else:
            verbose_names_of_interest = self.DEFAULT_SOCIAL_ORDER

        # Create a mapping from verbose_name to field_name
        verbose_name_to_field = {
            field.verbose_name: field.name for field in self._meta.fields
        }

        field_values = {}
        for verbose_name in verbose_names_of_interest:
            field_name = verbose_name_to_field.get(verbose_name)
            if field_name and hasattr(self, field_name) and getattr(self, field_name):
                field_value = getattr(self, field_name)
                field_values[verbose_name] = field_value

        return field_values

    class Meta:
        ordering = ('name', )
        verbose_name = 'periodista'
        verbose_name_plural = 'periodistas'


class Location(Model):
    city = CharField('ciudad', max_length=50)
    country = CharField('país', max_length=50)
    date_created = DateTimeField('fecha de creación', auto_now_add=True)

    def __str__(self):
        return '%s, %s' % (self.city, self.country)

    class Meta:
        get_latest_by = 'date_created'
        ordering = ('country', 'city')
        unique_together = ('city', 'country')
        verbose_name = 'ubicación'
        verbose_name_plural = 'ubicaciones'


class ArticleBase(Model, CT):
    TYPE_CHOICES = settings.CORE_ARTICLE_TYPES

    DISPLAY_CHOICES = (
        ('I', 'Imagen'),
        ('A', 'Audio'),
        ('V', 'Video'),
    )

    HEADER_DISPLAY_CHOICES = (
        ('FW', 'Ancho completo'),
        ('BG', 'Grande'),
    )

    HOME_HEADER_DISPLAY_CHOICES = (
        ('FW', 'Ancho completo'),
        ('FF', 'Medio y medio'),
        ('SM', 'Chico'),
    )

    publication = ForeignKey(
        Publication,
        on_delete=CASCADE,
        verbose_name='publicación',
        blank=True,
        null=True,
        related_name='articles_%(app_label)s',
    )
    type = CharField('tipo', max_length=2, choices=TYPE_CHOICES, blank=True, null=True, db_index=True)
    headline = CharField('título', max_length=200, help_text='Se muestra en la portada y en el artículo.')
    keywords = CharField(
        'titulín', max_length=45, blank=True, null=True, help_text='Se muestra encima del título en portada.'
    )
    slug = SlugField('slug', max_length=200)
    url_path = CharField(max_length=512, db_index=True)
    deck = TextField(
        'descripción', blank=True, null=True, help_text='Se muestra en la página del artículo debajo del título.'
    )
    lead = TextField(
        'copete', blank=True, null=True, help_text='Se muestra en la página del artículo debajo de la bajada.'
    )
    body = MartorField("cuerpo")
    header_display = CharField(
        'tipo de cabezal', max_length=2, choices=HEADER_DISPLAY_CHOICES, blank=True, null=True, default='BG'
    )
    home_header_display = CharField(
        'tipo de cabezal cuando es portada',
        max_length=2,
        choices=HOME_HEADER_DISPLAY_CHOICES,
        blank=True,
        null=True,
        default='SM',
    )
    home_lead = TextField('bajada en portada', blank=True, null=True, help_text='Bajada del artículo en portada.')
    home_display = CharField('mostrar en portada', max_length=2, choices=DISPLAY_CHOICES, blank=True, null=True)
    home_top_deck = TextField(
        'bajada en destacados',
        blank=True,
        null=True,
        help_text=(
            'Se muestra en los destacados de la portada, en el caso de estar vacío se muestra la bajada del artículo.'
        ),
    )
    byline = ManyToManyField(
        Journalist,
        verbose_name='autor/es',
        related_name='articles_%(app_label)s',
        blank=True,
    )
    only_initials = BooleanField(
        'sólo iniciales',
        default=False,
        help_text=(
            'Marque esta opción para que en la firma del artículo se muestren únicamente las iniciales del autor.'
        ),
    )
    latitude = DecimalField('latitud', max_digits=10, decimal_places=6, blank=True, null=True)
    longitude = DecimalField('longitud', max_digits=10, decimal_places=6, blank=True, null=True)
    location = ForeignKey(
        Location,
        on_delete=CASCADE,
        verbose_name='ubicación',
        related_name='articles_%(app_label)s',
        blank=True,
        null=True,
    )
    is_published = BooleanField('publicado', default=True, db_index=True)
    date_published = DateTimeField('fecha de publicación', null=True, db_index=True)
    date_created = DateTimeField('fecha de creación', auto_now_add=True, db_index=True)
    last_modified = DateTimeField('última actualización', auto_now=True)
    views = PositiveIntegerField('vistas', default=0, db_index=True)
    allow_comments = BooleanField('Habilitar comentarios', default=True)
    created_by = ForeignKey(
        User,
        on_delete=CASCADE,
        verbose_name='creado por',
        related_name='created_articles_%(app_label)s',
        editable=False,
        blank=False,
        null=True,
    )
    photo = ForeignKey(Photo, on_delete=CASCADE, blank=True, null=True, verbose_name='imagen')
    gallery = ForeignKey(Gallery, on_delete=CASCADE, verbose_name='galería', blank=True, null=True)
    video = ForeignKey(
        Video,
        on_delete=CASCADE,
        verbose_name='video',
        related_name='articles_%(app_label)s',
        blank=True,
        null=True,
    )
    youtube_video = ForeignKey(YouTubeVideo, on_delete=CASCADE, verbose_name='video de YouTube', blank=True, null=True)
    audio = ForeignKey(
        Audio,
        on_delete=CASCADE,
        verbose_name='audio',
        related_name='articles_%(app_label)s',
        blank=True,
        null=True,
    )
    tags = TagField(verbose_name='etiquetas', blank=True, null=True)
    allow_related = BooleanField(
        'mostrar en artículos relacionados', default=True, blank=False, null=False, db_index=True
    )
    show_related_articles = BooleanField(
        'mostrar artículos relacionados dentro de este artículo', default=True, blank=False, null=False
    )
    public = BooleanField('Artículo libre', default=False)
    full_restricted = BooleanField(
        'Disponible sólo para suscriptores',
        default=False,
        help_text="Acceso solamente a usuarios que tengan alguna suscripción activa."
    )

    published = PublishedArticleManager()

    def __str__(self):
        return self.headline

    def save(self, *args, **kwargs):
        from .utils import add_punctuation

        for attr in ('headline', 'deck', 'lead', 'body'):
            if getattr(self, attr, None):
                setattr(self, attr, getattr(self, attr).strip())
                setattr(self, attr, smart_quotes(getattr(self, attr)))
        for attr in ('deck', 'lead', 'body'):
            if getattr(self, attr, None):
                setattr(self, attr, add_punctuation(getattr(self, attr, '')))

        self.slug = slugify(cleanhtml(ldmarkup(self.headline)))

        # full restricted / open consistency checks
        # 1. If open => full_restricted == False
        # 2. If full_restricted => open == False
        if self.is_published and self.is_public() and self.full_restricted:
            raise Exception(
                "Un artículo publicado no puede ser libre y además estar disponible sólo para suscriptores."
            )

        # other checks

        nowval = now()

        if self.is_published:
            if not self.date_published:
                self.date_published = nowval
            if not settings.DEBUG:
                try:
                    ping_google()
                except Exception:
                    pass
        else:
            self.date_published = None

        date_value = self.date_published or self.date_created or nowval
        # No puede haber otro publicado con date_published en el mismo mes que date_value o no publicado con
        # date_created en el mismo mes que date_value, con el mismo slug. TODO: translate this comment to english.
        if isinstance(date_value, str):
            # needed if for example, assigning from a shell using strings for dates.
            # TODO: this only works if elasticsearch is off (improve this)
            date_value = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
        targets = Article.objects.filter(
            Q(is_published=True) & Q(date_published__year=date_value.year) & Q(date_published__month=date_value.month)
            | Q(is_published=False) & Q(date_created__year=date_value.year) & Q(date_created__month=date_value.month),
            slug=self.slug,
        )
        if self.id:
            targets = targets.exclude(id=self.id)
        if targets:
            # TODO: IntegrityError may be better exception to raise
            raise Exception('Ya existe un artículo en ese mes con el mismo título.')

        super(ArticleBase, self).save(*args, **kwargs)

    def is_photo_article(self):
        return self.type == settings.CORE_PHOTO_ARTICLE

    def has_deck(self):
        return bool(self.deck)

    def get_deck(self):
        if self.deck:
            return self.deck
        return ''

    def has_lead(self):
        return bool(self.lead)

    def get_lead(self):
        return self.lead or self.body[: self.body.find('\n')]

    def get_keywords(self):
        if self.keywords:
            return self.keywords
        return None

    def has_byline(self):
        return self.byline.exists()

    def get_authors(self):
        return self.byline.all()

    def get_tags(self):
        return Tag.objects.get_for_object(self)

    def get_absolute_url(self):
        # TODO: remove this "or" after proove that obj can't be saved with url_path blank or None
        return self.url_path or self.build_url_path()

    def build_url_path(self):
        date_value = self.date_published or self.date_created
        if isinstance(date_value, str):
            # needed if for example, assigning from a shell using strings for dates.
            # TODO: this only works if elasticsearch is off (improve this)
            date_value = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
        reverse_kwargs = {'year': date_value.year, 'month': date_value.month, 'slug': self.slug}
        main_section = getattr(self, 'main_section', None)
        if main_section:
            if main_section.edition.publication.slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL:
                if main_section.section.category:
                    reverse_kwargs['domain_slug'] = main_section.section.category.slug
            else:
                reverse_kwargs['domain_slug'] = main_section.edition.publication.slug
        return reverse('article_detail', kwargs=reverse_kwargs)

    def get_discussion_url(self):
        return '%sdiscusion/' % self.get_absolute_url()

    def get_comment_post_url(self):
        return self.get_discussion_url()

    def get_feed_url(self):
        return '/feeds/discusion/%(year)i/%(month)i/%(slug)s/' % {
            'year': self.date_published.year,
            'month': self.date_published.month,
            'slug': self.slug,
        }

    def get_app_body(self):
        """Returns the body formatted for the app"""
        # TODO: raising encoding error, fix asap.
        # TODO: what does "for the app" mean?
        # TODO: check if the first TODO is still happening
        return render_to_string('article/app_body.html', {'article': self})

    def surl(self):
        return mark_safe('<a href="/short/A/%i/">sURL</a>' % self.id)

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
            change_url = reverse('admin:core_article_change', args=(self.id,))
            return mark_safe("<a href='%s' target='_blank'>Editar</a>" % change_url)
        else:
            return 'No Existe'

    def is_public(self):
        return self.public

    def get_photos_wo_cover(self):
        return self.gallery.photos.exclude(id__exact=self.photo.id if self.photo else 0)

    def get_audio_length(self, seconds=False):
        if self.audio:
            try:
                td = timedelta(seconds=int(mutagen.File(self.audio.file).info.length))
            except FileNotFoundError:
                pass
            else:
                if seconds:
                    return td.seconds
                strtd = str(td)
                return strtd.split(":", 1)[-1] if td.seconds < 3600 else strtd

    def has_photo(self):
        try:
            return bool(self.photo)
        except PhotoExtended.DoesNotExist:
            return False

    def photo_image_file_exists(self):
        try:
            result = self.has_photo() and bool(self.photo.image.file)
        except IOError:
            result = False
        return result

    def photo_render_allowed(self):
        return self.photo_image_file_exists() and self.photo.is_public

    def amp_video_poster_image_url(self):
        """
        TODO: This approach should be used in all site calls to "get_<size>_url", helped by a mapping setting, then
              each "get" method knows which size should ask for (and calls the "generic" method that makes the checks
              like this method does).
        """
        if self.photo_render_allowed():
            med_url = self.photo.get_med_url()  # this call will generate the "med" image if it not exist in cache
            # but check again (cache can be old or broken)
            if isfile(join(settings.MEDIA_ROOT, self.photo.get_med_filename())):
                return med_url
        return settings.STATIC_URL + "img/amp_video_default_poster.png"  # default poster (broken or not allowed/exist)

    @property
    def photo_width(self):
        try:
            result = self.photo.image.width
        except RuntimeError:
            result = self.photo.extended.width
        return result

    @property
    def photo_height(self):
        try:
            result = self.photo.image.height
        except RuntimeError:
            result = self.photo.extended.height
        return result

    @property
    def photo_layout(self):
        return 'landscape' if not self.photo or self.photo.extended.is_landscape else 'portrait'

    @property
    def photo_filename_ext(self):
        return self.photo_image_file_exists() and splitext(self.photo.image_filename())[1].lower()

    @property
    def photo_type(self):
        return self.photo.extended.get_type_display()

    @property
    def photo_author(self):
        return self.photo and self.photo.extended.photographer

    @property
    def photo_caption(self):
        result = self.photo.caption or "Foto principal del artículo '%s'" % remove_markup(self.headline)
        if self.photo_author:
            result += ' · %s: %s' % (self.photo_type, self.photo_author)
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

    def formatted_body(self, amp=False):
        return (amp_ldmarkup if amp else ldmarkup)(self.body, self.id)

    def unformatted_body(self):
        return cleanhtml(self.formatted_body())

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
            mins = str(old_div(total_sec, 60)) + ' minutos'
            return mins

    def date_published_isoformat(self):
        return datetime_isoformat(self.date_published)

    def last_modified_isoformat(self):
        return datetime_isoformat(self.last_modified)

    def date_published_seconds_ago(self):
        return (now() - self.date_published).total_seconds()

    def datetime_published_verbose(self, day_name_and_time=True):
        locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)
        format_st = "{dt.day} de {dt:%B de %Y}"

        if day_name_and_time:
            format_st = "{dt:%A} " + format_st + ", {dt:%H:%M}"
        else:
            # call for cards, allow to hide year and a custom fmt by settings
            if (
                getattr(settings, 'CORE_ARTICLE_CARDS_DATE_PUBLISHED_HIDE_SAMEYEAR', False)
                and now().year == self.date_published.year
            ):
                format_st = getattr(settings, 'CORE_ARTICLE_CARDS_DATE_PUBLISHED_SAMEYEAR_FMT', "{dt.day} de {dt:%B}")

        return format_st.format(dt=template_localtime(self.date_published)).lower().capitalize()

    def date_published_verbose(self):
        if settings.CORE_ARTICLE_CARDS_DATE_PUBLISHED_USE_AGO:
            total_seconds = self.date_published_seconds_ago()
            if total_seconds < 60:
                verbose_date = "Hace segundos"
            elif total_seconds < 60 * 60:
                minutes = int(old_div(total_seconds, 60))
                verbose_date = "Hace %d minuto" % minutes
                if minutes > 1:
                    verbose_date += 's'
            elif total_seconds < 60 * 60 * 24:
                hours = int(old_div(old_div(total_seconds, 60), 60))
                verbose_date = "Hace %d hora" % hours
                if hours > 1:
                    verbose_date += 's'
            elif total_seconds < 60 * 60 * 24 * 2:
                verbose_date = "Ayer"
            elif total_seconds < 60 * 60 * 24 * 8:
                verbose_date = "Hace %d días" % (old_div(old_div(old_div(total_seconds, 60), 60), 24))
            else:
                verbose_date = self.datetime_published_verbose(False)
        else:
            verbose_date = self.datetime_published_verbose(False)
        return verbose_date

    class Meta:
        abstract = True
        get_latest_by = 'date_published'
        ordering = ('-date_published',)
        verbose_name = 'artículo'
        verbose_name_plural = 'artículos'
        indexes = [Index(fields=['type', 'date_published', 'is_published'])]


class Article(ArticleBase):
    objects = Manager()  # needed because the parent class is abstract
    sections = ManyToManyField(
        Section,
        verbose_name='sección',
        blank=False,
        through='ArticleRel',
        related_name='articles_%(app_label)s',
    )
    main_section = ForeignKey(
        'ArticleRel',
        verbose_name='publicación principal',
        blank=True,
        null=True,
        related_name='main',
        on_delete=SET_NULL,
    )
    viewed_by = ManyToManyField(
        User,
        verbose_name='visto por',
        blank=True,
        editable=False,
        through='ArticleViewedBy',
        related_name='viewed_articles_%(app_label)s',
    )
    additional_access = ManyToManyField(
        Publication,
        verbose_name='extender acceso a suscriptores por publicación',
        help_text=(
            'Además de los permisos que automáticamente se establecen según dónde se publica el artículo, '
            'se dará el mismo nivel de acceso a los suscriptores de las publicaciones marcadas aquí.'
        ),
        blank=True,
    )
    newsletter_featured = BooleanField('destacado en newsletter', default=False)
    ipfs_upload = BooleanField('Publicar en IPFS', default=False)
    ipfs_cid = TextField('id de IPFS', blank=True, null=True, help_text='CID del artículo en IPFS')
    # alternative fields
    alt_title_metadata = CharField(
        'título alternativo para metadatos',
        blank=True,
        null=True,
        max_length=200,
        help_text=mark_safe(
            'Aplica a metadatos: meta title, Open Graph y Schema en el '
        ) + escape("<head>") + mark_safe(' de la página del artículo.<br>Si se deja vacío aplica Título principal.')
    )
    alt_desc_metadata = TextField(
        'descripción alternativa para metadatos',
        blank=True,
        null=True,
        help_text=mark_safe(
            'Aplica a metadatos: meta description, Open Graph y Schema en el '
        ) + escape("<head>")
        + mark_safe(' de la página del artículo.<br>Si se deja vacío aplica Descripción principal.')
    )
    alt_title_newsletters = CharField(
        'título alternativo para newsletters',
        blank=True,
        null=True,
        max_length=200,
        help_text=mark_safe(
            'Aplica en newsletters donde aparezca el artículo.<br>Si se deja vacío aplica Título principal.'
        )
    )
    alt_desc_newsletters = TextField(
        'descripción alternativa para newsletters',
        blank=True,
        null=True,
        help_text=mark_safe(
            'Aplica en newsletters donde aparezca el artículo.<br>Si se deja vacío aplica Descripción principal'
        )
    )
    # SuperDesk article ID
    sp_id = CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs):

        if self.pk and self.sections:
            # Only valid if the instance has already been saved.
            # TODO: this should be reviewed, what happens if another article
            # in the same edition-section is viewed (viewed implies saving)
            for ar in ArticleRel.objects.filter(article=self):
                if not ar.position:
                    ar.position = ArticleRel.objects.filter(edition=ar.edition, section=ar.section).count() + 1

        # TODO: also this if block should be reviewed (broken)
        # if self.home_top and self.top_position is None:
        #    self.top_position = Article.objects.filter(
        #        edition=self.edition, home_top=self.home_top).count() + 1
        if self.type == settings.CORE_HTML_ARTICLE:
            self.headline = 'HTML | %s | %s | %s' % (str(self.edition), str(self.section), str(self.section_position))

        old_url_path = self.url_path
        super(Article, self).save(*args, **kwargs)
        # the instance has already been saved, force_insert should be turned into False if a save is called again
        kwargs['force_insert'] = False

        # execute this steps only if not called from admin, admin already does this work in a similar way and order.
        from_admin = getattr(self, 'admin', False)
        if not from_admin:
            self.refresh_from_db()
            new_url_path = self.build_url_path()
            url_changed = old_url_path != new_url_path

            if url_changed:
                self.url_path = new_url_path
                self.do_ipfs_upload()
                super(Article, self).save(*args, **kwargs)
                talk_url = getattr(settings, 'TALK_URL', None)
                # if this is an insert, old_url_path is '', then skip talk update
                if old_url_path and talk_url and not settings.DEBUG:
                    # the article has a new url, we need to update it in Coral-Talk using the API
                    # but don't do this in DEBUG mode to avoid updates with local urls in Coral
                    try:
                        update_article_url_in_coral_talk(self.id, new_url_path)
                    except (ConnectionError, ValueError, KeyError, AssertionError, TypeError):
                        # fail silently because we should not break any script or shell that is saving the article
                        pass
            elif self.do_ipfs_upload():
                super(Article, self).save(*args, **kwargs)

            # add to history the new url
            if not ArticleUrlHistory.objects.filter(article=self, absolute_url=new_url_path).exists():
                ArticleUrlHistory.objects.create(article=self, absolute_url=new_url_path)

        elif self.do_ipfs_upload():
            super(Article, self).save(*args, **kwargs)

    def do_ipfs_upload(self):
        """
        Do the upload to IPFS (if set and configured) and returns True if the upload was succesful or cid was cleaned
        """
        if self.ipfs_upload:
            # TODO: An improvement can be made to upload if only relevant fields were modified, using approaches from
            #       https://stackoverflow.com/questions/1355150/when-saving-how-can-you-check-if-a-field-has-changed
            ipfs_token = getattr(settings, "IPFS_TOKEN", None)
            if not ipfs_token:
                raise ImproperlyConfigured("La configuración necesaria para publicar en IPFS no está definida.")
            else:
                try:
                    w3 = w3storage.API(token=ipfs_token)
                    cid = w3.post_upload(
                        (
                            "%s-core.Article-%s" % (settings.SITE_DOMAIN, str(self.id)),
                            render_to_string(
                                "article/detail_ipfs_upload.html",
                                {
                                    "site_url": settings.SITE_URL_SD,
                                    "ipfs_cid": self.ipfs_cid,
                                    "headline": self.headline,
                                    "date_published": self.date_published,
                                    "authors": ", ".join([author.name for author in self.get_authors()]),
                                    "section": self.publication_section(),
                                    "tags": self.tags,
                                    "photo": self.photo if self.photo and self.photo.is_public else None,
                                    "photo_author": self.photo_author.name if self.photo_author else None,
                                    "lead": self.lead,
                                    "deck": self.deck,
                                    "body": self.body,
                                },
                            ),
                        )
                    )
                except Exception as e:
                    # TODO: think what can we raise or do here
                    if settings.DEBUG:
                        print(e)
                else:
                    self.ipfs_cid = cid
                    return True
        elif self.ipfs_cid:
            # This will drop any reference to this article in IPFS, and seems to be the right thing to do when the
            # field "ipfs_upload" was saved unchecked, note that there is no need to "delete" any data in IPFS since
            # the only way to retrieve data from IPFS is knowning the "cid".
            self.ipfs_cid = None
            return True

    def publications(self):
        return set([ar.edition.publication for ar in self.articlerel_set.select_related('edition__publication')])

    def get_publications(self):
        return ', '.join([p.name for p in self.publications()])

    get_publications.short_description = 'publicaciones'

    def get_section(self, category=None):
        """
        If category_slug is given, the result will be "filtered" by category, if this filtered set is not empty, the
        result will be one of them, otherwise If the set is empty (or no category_slug is given) it returns the main
        section where this article is published in, or the first section found if no main_section.
        TODO: unify with self.publication_section
        """
        result, main_section = None, None
        try:
            if self.main_section:
                main_section = self.main_section.section
                if not category or main_section.category == category:
                    result = main_section
        except ArticleRel.DoesNotExist:
            pass
        # return first match by category, if no match at all, return main or first without filtering
        s = self.sections
        if not result:
            if category:
                result = s.filter(category=category).first()
        return result or (main_section or s.first())

    @property
    def section(self):
        return self.get_section()

    def last_published_by_publication_slug(self, publication_slug=None):
        """
        Returns the last date published of the article in the publication slug given by param, if no given, use anyone.
        If no editions, or no editions found for the publication given, return the article's date_published.
        """
        if self.is_published:
            try:
                filter_kwargs = {'article': self}
                if publication_slug:
                    filter_kwargs['edition__publication__slug'] = publication_slug
                result = (
                    Edition.objects.filter(
                        id__in=[v[0] for v in ArticleRel.objects.filter(**filter_kwargs).values_list('edition')]
                    )
                    .order_by('-date_published')[0]
                    .date_published
                )
            except IndexError:
                result = self.date_published.date()
            return result

    def last_published_by_category(self, category):
        """
        Returns the last date published of the article inside a section that has the category passed by param.
        If no editions found, return the article's date_published.
        """
        if self.is_published:
            try:
                result = (
                    Edition.objects.filter(
                        id__in=[
                            v[0]
                            for v in ArticleRel.objects.filter(
                                article=self, section__in=category.section_set.all()
                            ).values_list('edition')
                        ]
                    )
                    .order_by('-date_published')[0]
                    .date_published
                )
            except IndexError:
                result = self.date_published.date()
            return result

    def last_published_by_category_slug(self, category_slug):
        if self.is_published:
            try:
                category = Category.objects.get(slug=category_slug)
            except Category.DoesNotExist:
                pass
            else:
                return self.last_published_by_category(category)

    def publication_section(self, publication=None):
        # TODO: unify with self.publication_section
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
                return s[0].section if s else self.sections.first()

            else:
                # Return the first
                return self.sections.first()

    def get_sections(self):
        return ', '.join([s.name for s in self.sections.distinct()])

    get_sections.short_description = 'secciones'

    def get_categories_slugs(self):
        return set(
            [
                s.category.slug
                for s in self.sections.filter(category__isnull=False).distinct().select_related('category')
            ]
        )

    def get_app_photo(self):
        """
        Returns the article's photo if any, if not, returns the article's
        section image (if any)
        """
        if self.photo:
            return self.photo
        else:
            section_imgs = self.sections.filter(imagen__isnull=False).values_list('imagen', flat=True)
            if section_imgs:
                return PhotoExtended(image=section_imgs[0])

    def is_restricted(self, consider_full=False):
        """
        If the article is pulished:
          If consider_full is True, the result will be True if this article is full_restricted.
          If consider_full is False or the previous result was False, then, the result will be True when the article's
            main pub is a restricted publication (by settings), plus the article is no public and has no extra-perms.
        """
        return (
            self.is_published
            and (
                consider_full
                and self.full_restricted
                or (
                    not self.is_public()
                    and self.main_section
                    and (
                        self.main_section.edition.publication.slug
                        in getattr(settings, 'CORE_RESTRICTED_PUBLICATIONS', ())
                    )
                    and not self.additional_access.exists()
                )
            )
        )

    def is_restricted_consider_full(self):
        """
        Wrapper for previous method
        """
        return self.is_restricted(True)

    def published_collections(self):
        return self.linked_collections.filter(**get_published_kwargs())

    def extensions_have_invalid_amp_tags(self):
        """
        When this happen, we should not announce that an AMP version o the page is availabke
        """
        invalid_tags = "base img picture video audio iframe frame frameset object param applet embed".split()
        for e in self.extensions.iterator():
            try:
                soup = BeautifulSoup(e.body, 'html.parser')
                for tag in invalid_tags:
                    if soup.find_all(tag):
                        return True
            except Exception:
                pass

    def nl_serialize(self, for_cover=False, publication=None, category=None, dates=True):
        authors = self.get_authors()
        section = self.publication_section(publication) if publication else self.get_section(category)
        result = {
            'id': self.id,
            'get_absolute_url': self.get_absolute_url(),
            'date_published': str(self.date_published.date()) if dates else self.date_published,
            'headline': self.headline,
            'home_lead': self.home_lead,
            'deck': self.deck,
            'has_byline': self.has_byline(),
            'get_authors': [
                {
                    "name": a.name,
                    "image": {"url": getattr(a.image, "url", None)} if a.image_file_exists() else {},
                } for a in authors
            ] if authors else None,
            "section": {
                "slug": section.slug, "name": section.name, "nl_display_name": section.nl_display_name()
            } if section else None,
        }
        if for_cover:
            result['body'] = self.body
            if self.photo:
                result['photo'] = {'get_700w_url': self.photo.get_700w_url(), 'caption': self.photo.caption}
                if self.photo_author:
                    result.update({'photo_author': self.photo_author.name, 'photo_type': self.photo_type})
        # extra data for category NLs
        if category:
            nl_email_template = get_category_template(category.slug, "newsletter")
            engine = Engine.get_default()
            try:
                extra_meta_template = engine.get_template(
                    join(dirname(nl_email_template), "article_extra_meta/%s.json" % category.slug)
                )
            except TemplateDoesNotExist:
                pass
            else:
                extra_meta_data = json.loads(extra_meta_template.render(Context({"article": self})))
                result.update(extra_meta_data)
        return result


class ArticleCollection(Article):
    objects = Manager()  # needed to avoid django to use the "published" as the default manager
    traversal_categorization = BooleanField(
        "categorización transversal",
        default=False,
        help_text="Si está marcada, prioriza la categorización de la colección para todo el contenido de la colección",
    )
    related_articles = ManyToManyField(
        Article,
        blank=False,
        through='ArticleCollectionRelated',
        related_name='linked_collections',
    )

    def related_articles_ordered(self):
        return self.related_articles.filter(**get_published_kwargs()).order_by("articlecollectionrelated")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if settings.ELASTICSEARCH_DSL_AUTOSYNC:
            # call post_save for the article obj to trigger potential elastic index upd
            post_save.send(Article, instance=self.article_ptr, using="default")

    class Meta:
        verbose_name = "colección"
        verbose_name_plural = "colecciones"
        indexes = []


class ArticleCollectionRelated(Model):
    collection = ForeignKey(ArticleCollection, related_name="linked_articles", on_delete=CASCADE)
    article = ForeignKey(
        Article, verbose_name='artículo', limit_choices_to={"articlecollection__isnull": True}, on_delete=CASCADE
    )
    position = PositiveSmallIntegerField('orden en la colección', default=None, null=True)

    def __str__(self):
        # Custom text version to be useful in the admin change form
        article_str = str(self.article)
        return " - ".join(
            [
                (("%d: " % self.position) if self.position else "")
                + (
                    date_format(
                        self.article.date_published,
                        format=settings.SHORT_DATE_FORMAT.replace('Y', 'y'),  # shorter format
                        use_l10n=True,
                    ) if self.article.is_published else "NP"
                ),
                (article_str[:10] + " …") if len(article_str) > 10 else article_str,
            ]
        )

    class Meta:
        verbose_name = "artículo vinculado"
        verbose_name_plural = "artículos vinculados"
        unique_together = ("collection", "article")
        ordering = ('position', '-article__date_published')


class ArticleRel(Model):
    """
    Relation to save the relative position of the article into the Article-Edition-Section relationship.
    NOTE: position cannot be blank because new rows marked as "main" in the admin inline, with position blank, and
          duplicated with another row (unique_together allows null values) will cause a 500 error when trying to set
          the row as main (another row can exist).
    """

    article = ForeignKey(Article, on_delete=CASCADE)
    edition = ForeignKey(Edition, on_delete=CASCADE)
    section = ForeignKey(Section, on_delete=CASCADE)
    position = PositiveSmallIntegerField('orden en la sección', default=None, null=True)
    home_top = BooleanField(
        'destacado en portada',
        default=False,
        help_text='Marque esta opción para que esta nota aparezca en los destacados de la edición.',
    )
    top_position = PositiveSmallIntegerField('orden', blank=True, null=True)

    def __str__(self):
        return '%s - %s' % (self.edition, self.section)

    @staticmethod
    def articles_count(max=None, section_slugs_only=[], debug=False):
        with connection.cursor() as cursor:
            subquery_part = """
                FROM core_article
                JOIN core_articlerel ON
                    core_article.id = core_articlerel.article_id
                JOIN core_section ON
                    core_articlerel.section_id = core_section.id
                JOIN core_edition ON
                    core_articlerel.edition_id = core_edition.id
                WHERE is_published AND core_edition.date_published <= CURRENT_DATE
            """
            if section_slugs_only:
                subquery_part += "AND core_section.slug IN (%s)" % ",".join("'%s'" % s for s in section_slugs_only)
            if max:
                query = "SELECT COUNT(*) FROM (SELECT DISTINCT core_article.id %s LIMIT %d) final" % (
                    subquery_part,
                    max,
                )
            else:
                query = "SELECT COUNT(DISTINCT core_article.id) " + subquery_part
            if debug:
                print(query)
            cursor.execute(query)
            return cursor.fetchone()[0]

    class Meta:
        ordering = ('position', '-article__date_published')
        unique_together = ('article', 'edition', 'section', 'position')


class ArticleViewedBy(Model):
    article = ForeignKey(Article, on_delete=CASCADE)
    user = ForeignKey(User, on_delete=CASCADE)
    viewed_at = DateTimeField(db_index=True)

    class Meta:
        unique_together = ('article', 'user')


class ArticleViews(Model):
    article = ForeignKey(Article, on_delete=CASCADE)
    day = DateField(db_index=True)
    views = PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('article', 'day')
        index_together = [('day', 'views')]


class CategoryHomeArticle(Model):
    home = ForeignKey('CategoryHome', on_delete=CASCADE)
    article = ForeignKey(
        Article,
        on_delete=CASCADE,
        verbose_name='artículo',
        related_name='home_articles',
        limit_choices_to={'is_published': True},
    )
    position = PositiveSmallIntegerField('publicado')  # a custom label useful in the CategoryHome admin change form
    fixed = BooleanField('fijo', default=False)

    def __str__(self):
        # also a custom text version to be useful in the CategoryHome admin change form
        try:
            result = (
                date_format(
                    self.article.last_published_by_category(self.home.category),
                    format=settings.SHORT_DATE_FORMAT.replace('Y', 'y'),  # shoter format
                    use_l10n=True,
                ) if self.article.is_published else "No publicado! "
            ) + ('-F' if self.article.photo_render_allowed() else '')
        except Exception:
            result = super().__str__()
        return result

    class Meta:
        ordering = ('position',)
        unique_together = ('home', 'position')


class CategoryHome(Model):
    category = OneToOneField(Category, on_delete=CASCADE, verbose_name='área', related_name='home')
    articles = ManyToManyField(Article, through=CategoryHomeArticle)

    def __str__(self):
        return '%s - %s' % (self.category, self.cover())

    def articles_ordered(self):
        return self.articles.filter(is_published=True).order_by('home_articles').prefetch_related(
            'main_section__edition__publication', 'main_section__section', 'photo__extended__photographer', 'byline'
        )

    def cover(self):
        """ Returns the article in the 1st position """
        return self.articles_ordered().first()

    def non_cover_articles(self):
        """ Returns the articles from 2nd position """
        return self.articles_ordered()[1:]

    def set_article(self, article, position):
        try:
            actual_article = CategoryHomeArticle.objects.get(home=self, position=position)
            if actual_article.article != article:
                actual_article.article = article
                actual_article.save()
        except CategoryHomeArticle.DoesNotExist:
            CategoryHomeArticle.objects.create(home=self, article=article, position=position)

    def dehole(self):
        # rearrange positions without holes
        for i, home_article in enumerate(self.categoryhomearticle_set.all(), 1):
            if home_article.position != i:
                home_article.position = i
                home_article.save()

    def print(self):
        for ha in self.categoryhomearticle_set.all():
            print('%d:\t%s\t%s' % (ha.position, ha.article.date_published.date(), ha.article))

    class Meta:
        verbose_name = 'portada de área'
        verbose_name_plural = 'portadas de área'
        ordering = ('category',)


class CategoryNewsletterArticle(Model):
    newsletter = ForeignKey('CategoryNewsletter', on_delete=CASCADE)
    article = ForeignKey(
        Article,
        on_delete=CASCADE,
        verbose_name='artículo',
        related_name='newsletter_articles',
        limit_choices_to={'is_published': True},
    )
    order = PositiveSmallIntegerField('orden', null=True, blank=True)
    featured = BooleanField('incluir sólo en bloque destacado', default=False)

    def __str__(self):
        # also a custom text version to be useful in the CategoryNewsletter admin change form
        return (
            date_format(
                self.article.last_published_by_category(self.newsletter.category),
                format=settings.SHORT_DATE_FORMAT.replace('Y', 'y'),  # shoter format
                use_l10n=True,
            ) if self.article.is_published else "No publicado! "
        ) + ('-F' if self.article.photo else '')

    class Meta:
        ordering = ('order',)


class CategoryNewsletter(Model):
    valid_until = DateTimeField('válida hasta')
    category = OneToOneField(Category, on_delete=CASCADE, verbose_name='área', related_name='newsletter')
    articles = ManyToManyField(Article, through=CategoryNewsletterArticle)

    def __str__(self):
        return '%s - %s' % (self.category, self.cover())

    def non_featured_articles(self):
        """
        Returns the non-featured articles qs
        """
        return self.articles.filter(newsletter_articles__featured=False)

    def cover(self):
        """
        Returns the non-featured article in the 1st position
        """
        non_featured = self.non_featured_articles()
        return non_featured.exists() and non_featured.order_by('newsletter_articles')[0]

    def non_cover_articles(self):
        """
        Returns the non-featured articles from 2nd position
        """
        non_featured = self.non_featured_articles()
        return non_featured.order_by('newsletter_articles')[1:] if non_featured.exists() else []

    def featured_articles(self):
        """
        Returns the featured articles qs
        """
        return self.articles.filter(newsletter_articles__featured=True)

    def featured_article(self):
        """
        Returns the featured article in the 1st position
        """
        featured = self.featured_articles()
        return featured.exists() and featured.order_by('newsletter_articles')[0]

    class Meta:
        verbose_name = 'newsletter de área'
        verbose_name_plural = 'newsletters de área'
        ordering = ('category',)


class ArticleExtension(Model):
    SIZE_CHOICES = (
        ('R', 'Regular'),
        ('M', 'Mediano'),
        ('F', 'Full'),
    )
    article = ForeignKey(Article, on_delete=CASCADE, verbose_name='artículo', related_name='extensions')
    headline = CharField('título', max_length=100, null=True, blank=True)
    body = TextField('cuerpo')
    size = CharField('size', max_length=1, choices=SIZE_CHOICES, default='R')
    background_color = CharField('background color', max_length=7, default='#eaeaea', null=True, blank=True)

    def __str__(self):
        return self.headline or ''

    def _is_published(self):
        return self.article.is_published

    is_published = property(_is_published)

    class Meta:
        ordering = ('article', 'headline')
        verbose_name = 'recuadro'
        verbose_name_plural = 'recuadros'


class ArticleBodyImage(Model):
    DISPLAY_CHOICES = (
        ('BG', 'Ancho regular'),
        ('MD', 'Ancho amplio'),
        ('FW', 'Ancho completo'),
    )
    article = ForeignKey(Article, on_delete=CASCADE, verbose_name='artículo', related_name='body_image')
    image = ForeignKey(Photo, on_delete=CASCADE, verbose_name='foto', related_name='photo')
    display = CharField('display', max_length=2, choices=DISPLAY_CHOICES, default='MD')

    def __str__(self):
        return (self.image.title or '') if self.image else ''

    class Meta:
        verbose_name = 'imagen'
        verbose_name_plural = 'imagenes'


class PrintOnlyArticle(Model):
    headline = CharField('título', max_length=100)
    deck = CharField('bajada', max_length=255, blank=True, null=True)
    edition = ForeignKey(Edition, on_delete=CASCADE, verbose_name='edición', related_name='print_only_articles')
    date_created = DateTimeField('fecha de creación', auto_now_add=True)

    def __str__(self):
        return self.headline or ''

    class Meta:
        get_latest_by = 'date_created'
        ordering = ('id',)
        unique_together = ('headline', 'edition')
        verbose_name = 'artículo impreso'
        verbose_name_plural = 'artículos impresos'


class ArticleUrlHistory(Model):
    article = ForeignKey(Article, on_delete=CASCADE)
    absolute_url = URLField(max_length=500, db_index=True)

    class Meta:
        unique_together = ('article', 'absolute_url')


class BreakingNewsModule(Model):
    is_published = BooleanField('publicado', default=False)
    headline = CharField('título', max_length=100)
    deck = CharField('bajada', max_length=255, blank=True, null=True)
    enable_notification = BooleanField('mostrar notificación de alerta', default=False)
    notification_url = URLField('URL destino de la notificación', blank=True, null=True)
    notification_text = CharField('texto de la notificación', max_length=255, blank=True, null=True)
    articles = ManyToManyField(Article, verbose_name='artículos relacionados', blank=True)
    embeds_headline = CharField('título de los incrustados', max_length=100, blank=True, null=True)
    embeds_description = CharField('descripción de los incrustados', max_length=255, blank=True, null=True)
    embed1_title = CharField('título de incrustado 1', max_length=100, blank=True, null=True)
    embed1_content = TextField('contenido de incrustado 1', blank=True, null=True)
    embed2_title = CharField('título de incrustado 2', max_length=100, blank=True, null=True)
    embed2_content = TextField('contenido de incrustado 2', blank=True, null=True)
    embed3_title = CharField('título de incrustado 3', max_length=100, blank=True, null=True)
    embed3_content = TextField('contenido de incrustado 3', blank=True, null=True)
    embed4_title = CharField('título de incrustado 4', max_length=100, blank=True, null=True)
    embed4_content = TextField('contenido de incrustado 4', blank=True, null=True)
    embed5_title = CharField('título de incrustado 5', max_length=100, blank=True, null=True)
    embed5_content = TextField('contenido de incrustado 5', blank=True, null=True)
    embed6_title = CharField('título de incrustado 6', max_length=100, blank=True, null=True)
    embed6_content = TextField('contenido de incrustado 6', blank=True, null=True)
    embed7_title = CharField('título de incrustado 7', max_length=100, blank=True, null=True)
    embed7_content = TextField('contenido de incrustado 7', blank=True, null=True)
    embed8_title = CharField('título de incrustado 8', max_length=100, blank=True, null=True)
    embed8_content = TextField('contenido de incrustado 8', blank=True, null=True)
    embed9_title = CharField('título de incrustado 9', max_length=100, blank=True, null=True)
    embed9_content = TextField('contenido de incrustado 9', blank=True, null=True)
    embed10_title = CharField('título de incrustado 10', max_length=100, blank=True, null=True)
    embed10_content = TextField('contenido de incrustado 10', blank=True, null=True)
    embed11_title = CharField('título de incrustado 11', max_length=100, blank=True, null=True)
    embed11_content = TextField('contenido de incrustado 11', blank=True, null=True)
    embed12_title = CharField('título de incrustado 12', max_length=100, blank=True, null=True)
    embed12_content = TextField('contenido de incrustado 12', blank=True, null=True)
    embed13_title = CharField('título de incrustado 13', max_length=100, blank=True, null=True)
    embed13_content = TextField('contenido de incrustado 13', blank=True, null=True)
    embed14_title = CharField('título de incrustado 14', max_length=100, blank=True, null=True)
    embed14_content = TextField('contenido de incrustado 14', blank=True, null=True)
    publications = ManyToManyField(Publication, verbose_name='portada de publicaciones', blank=True)
    categories = ManyToManyField(Category, verbose_name='portada de áreas', blank=True)

    def __str__(self):
        return self.headline or ''

    def covers(self):
        return ', '.join([str(p) for p in self.publications.all()] + [str(c) for c in self.categories.all()])

    covers.short_description = 'portadas'

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
        verbose_name = 'módulo de último momento'
        verbose_name_plural = 'módulos de último momento'


def get_publishing_datetime():
    today = now().date()
    publishing_hour, publishing_minute = [int(i) for i in settings.PUBLISHING_TIME.split(':')]
    return make_aware(datetime(today.year, today.month, today.day, publishing_hour, publishing_minute))


def get_published_date():
    # TODO: check usage, remove if not used, the same for get_publishing_datetime
    nowval = now()
    publishing = get_publishing_datetime()
    publishing_date = datetime(publishing.year, publishing.month, publishing.day).date()
    if nowval > publishing:
        return publishing_date
    return publishing_date - timedelta(1)


def get_current_edition(publication=None):
    """
    Return last edition of publication if given, or the publications using root url as their home page if the
    publication slug is not given.
    """
    nowval = now()
    today, filters = nowval.date(), {}
    publishing_hour, publishing_minute = [int(i) for i in settings.PUBLISHING_TIME.split(':')]
    publishing = make_aware(datetime(today.year, today.month, today.day, publishing_hour, publishing_minute))

    if publication:
        filters['publication'] = publication.id
    else:
        filters['publication__in'] = Publication.objects.filter(
            slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL
        ).values_list('id', flat=True)

    filters['date_published__lt' + ('e' if nowval > publishing else '')] = today
    try:
        results = Edition.objects.filter(**filters)
        result = results.latest()
        if not publication and result.publication.slug != settings.DEFAULT_PUB:
            # give priority to default pub if no pub given and "latest" include at least one for the default pub
            return results.filter(
                publication__slug=settings.DEFAULT_PUB, date_published=result.date_published
            ).first() or result
        else:
            return result
    except Exception as e:
        if settings.DEBUG:
            print('ERROR: %s' % e)
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
    today, current_edition = now().date(), get_current_edition()
    next_editions = Edition.objects.filter(
        publication__public=True,
        publication__slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL,
        date_published__gt=current_edition.date_published if current_edition else today,
    ).order_by('date_published')
    editions_ids = ([str(current_edition.id)] if current_edition else []) + (
        [str(next_editions[0].id)] if next_editions else []
    )

    # editions for all the other publications (current and "next")
    for p in Publication.objects.filter(public=True).exclude(slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL):
        current_edition = get_current_edition(p)
        next_editions = Edition.objects.filter(
            publication=p, date_published__gt=current_edition.date_published if current_edition else today
        ).order_by('date_published')
        editions_ids += ([str(current_edition.id)] if current_edition else []) + (
            [str(next_editions[0].id)] if next_editions else []
        )

    return Article.published.extra(
        where=[
            'core_article.id=core_articlerel.article_id',
            'core_articlerel.edition_id IN (%s)' % ','.join(editions_ids),
        ],
        tables=['core_articlerel'],
    ).distinct()


class DeviceSubscribed(Model):
    subscription_info = CharField(max_length=1024)
    time_created = DateTimeField(auto_now_add=True)
    user = ForeignKey(User, on_delete=CASCADE)

    def __str__(self):
        return "%s %d (user %s)" % (self.__class__.__name__, self.id, self.user)


class PushNotification(Model):
    message = CharField(u'Mensaje', max_length=500)
    article = ForeignKey(Article, on_delete=CASCADE, verbose_name=u'Articulo')
    sent = DateTimeField(u'Fecha de envio', null=True)
    tag = CharField(u'Tag', max_length=15, null=True, blank=True)
    overwrite = BooleanField(u'Sobrescribir notificacion', default=False)

    def __str__(self):
        return "%s - %s" % (self.tag, self.message)
