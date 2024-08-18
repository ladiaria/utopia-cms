# -*- coding: utf-8 -*-

from star_ratings.models import Rating

from django.conf import settings
from django.db.models import CASCADE
from django.db.models import Model, CharField, TextField, ForeignKey
from django.db.models.fields import DateTimeField, SlugField, PositiveSmallIntegerField, BooleanField, URLField
from django.db.models.fields.files import ImageField
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.timezone import datetime, now
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation

from core.models import CT

from .choices import LIVE_EMBED_EVENT_ACCESS_TYPES


class CategoriaEvento(Model):
    nombre = CharField('nombre', max_length=100, blank=True, null=True)
    order = PositiveSmallIntegerField(u'orden en cartelera', default=0)
    slug = SlugField(db_index=True)

    def current_events(self):
        today_min = datetime.combine(now().date(), datetime.min.time())
        return self.eventobase_set.select_related().order_by('start').filter(end__gte=today_min)[:20]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('categoria_evento', kwargs={'slug': self.slug})


class EventoBaseCategoryAuto(Model):
    def save(self, *args, **kwargs):
        self.type = self._meta.module_name
        self.categoria, created = CategoriaEvento.objects.get_or_create(slug=self.type, nombre=self.type)
        super(EventoBaseCategoryAuto, self).save(*args, **kwargs)

    class Meta:
        abstract = True


class EventoBase(Model, CT):
    categoria = ForeignKey(CategoriaEvento, on_delete=CASCADE)
    title = CharField('titulo', max_length=250)
    description = TextField('descripción', blank=True, null=True)
    slug = SlugField(db_index=True)
    rating = GenericRelation(Rating)
    start = DateTimeField('comienzo')
    end = DateTimeField('fin')
    precio = CharField('precio', max_length=250)
    poster = ImageField(upload_to='cartelera/posters', blank=True, null=True)
    type = CharField(max_length=250)

    def __str__(self):
        return self.title

    def render(self):
        return render_to_string(
            ['cartelera/%s_lead.html' % self.categoria.slug, 'cartelera/evento_lead.html'],
            {'%s' % self.categoria.slug: self},
        )

    def get_absolute_url(self):
        return reverse('evento', kwargs={'slug': self.slug})


class ArchivedEvent(Model):
    access_type = CharField(u'acceso al evento', max_length=1, choices=LIVE_EMBED_EVENT_ACCESS_TYPES, default='s')
    title = CharField(u'título', max_length=255)
    embed_content = TextField(u'contenido incrustado', blank=True, null=True)

    def is_free(self):
        return self.access_type == u'f'

    def get_absolute_url(self):
        return reverse('cartelera-archive', kwargs={'archived_event_id': self.id})

    def link(self):
        href = (settings.SITE_URL_SD + self.get_absolute_url()) if self.id else None
        return mark_safe('<a href="%s">%s</a>' % (href, href)) if href else None

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = u'evento archivado'
        verbose_name_plural = u'eventos archivados'


class LiveEmbedEvent(Model):
    """
    This is an event not inherited from BaseEvent because it doesn't need some
    required attributes, in the future this app can be refactored and we can
    change BaseEvent to a more minimal version.
    This events will be used for the metadata needed to display a live event
    embeded in a page of our site.
    """

    active = BooleanField(u'activo', default=False)
    access_type = CharField(u'acceso al evento', max_length=1, choices=LIVE_EMBED_EVENT_ACCESS_TYPES, default='s')
    in_home = BooleanField(u'agregar a portada', default=False)
    notification = BooleanField(u'mostrar notificación en artículos', default=False)
    notification_text = CharField(u'texto', max_length=255, null=True, blank=True)
    notification_url = URLField(u'url', null=True, blank=True)
    title = CharField(u'título', max_length=255)
    embed_content = TextField(u'contenido incrustado', blank=True, null=True)
    embed_chat = TextField(u'chat incrustado', blank=True, null=True)

    def is_free(self):
        return self.access_type == u'f'

    def clean(self):
        from django.core.exceptions import ValidationError

        active_now = LiveEmbedEvent.objects.filter(active=True)
        if self.active:
            if active_now.exclude(id=self.id) if self.id else active_now:
                # Don't allow more than one active instance
                raise ValidationError(u'Only one event can be active at the same time.')
            if not self.embed_content:
                raise ValidationError(u'Embed content should be set if the event is active.')

    def save(self, *args, **kwargs):
        self.full_clean()  # calls self.clean() as well cleans other fields
        return super(LiveEmbedEvent, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = u'evento en vivo'
        verbose_name_plural = u'eventos en vivo'


class Lugar(Model):
    nombre = CharField('nombre', max_length=100, blank=True, null=True)
    slug = SlugField(db_index=True)
    prepopulated_fields = {"slug": ("nombre",)}
    address = TextField('dirección', blank=True, null=True)
    phones = CharField('telefonos', max_length=250)

    class Meta:
        abstract = True

    def __str__(self):
        return self.nombre


def get_content_type(name):
    contenttype, created = ContentType.objects.get_or_create(app_label="cartelera", model=name)
    return contenttype


class Pelicula(EventoBase, EventoBaseCategoryAuto):
    @property
    def contenttype(self):
        return get_content_type(self.__name__)

    def get_absolute_url(self):
        return reverse('pelicula', args=[self.slug])


class ObraTeatro(EventoBase, EventoBaseCategoryAuto):
    @property
    def contenttype(self):
        return get_content_type(self.__name__)

    def get_absolute_url(self):
        return reverse('obrateatro', args=[self.slug])


class Cine(Lugar):
    @property
    def contenttype(self):
        return get_content_type(self.__name__)

    def get_absolute_url(self):
        return reverse('cine', args=[self.slug])


class Teatro(Lugar):
    @property
    def contenttype(self):
        return get_content_type(self.__name__)


class Evento(EventoBase):
    @property
    def contenttype(self):
        return get_content_type(self.__name__)


class Horarios(Model):
    horarios = TextField('horarios', blank=True, null=True)

    class Meta:
        abstract = True


class PeliculaEnCine(Horarios):
    pelicula = ForeignKey(Pelicula, on_delete=CASCADE, related_name='horarios')
    cine = ForeignKey(Cine, on_delete=CASCADE, related_name='horarios')


class ObraEnTeatro(Horarios):
    obra = ForeignKey(ObraTeatro, on_delete=CASCADE, related_name='horarios')
    teatro = ForeignKey(Teatro, on_delete=CASCADE, related_name='horarios')
