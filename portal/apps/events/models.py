# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db.models import CASCADE
from django.db.models import (
    Model,
    CharField,
    TextField,
    DateTimeField,
    BooleanField,
    SlugField,
    ManyToManyField,
    ForeignKey,
    ImageField,
    permalink,
    EmailField,
)
from django.urls import reverse
from thedaily.models import Subscriber


class Location(Model):
    name = CharField('nombre', max_length=50)
    address = CharField(u'dirección', max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'lugar'
        verbose_name_plural = 'lugares'


class Artist(Model):
    name = CharField('nombre', max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'artista'
        verbose_name_plural = 'artistas'


class BaseEvent(Model):
    location = ForeignKey(Location, on_delete=CASCADE, verbose_name='lugar')
    date = DateTimeField('fecha')
    title = CharField(u'título', max_length=255)
    image = ImageField(u'imagen', blank=True, null=True, upload_to="eventos")
    description = TextField(u'descripción', blank=True, null=True)
    published = BooleanField('publicado', default=False)

    def __str__(self):
        return self.title

    def short(self):
        if len(self.description) < 200:
            return self.description
        else:
            return self.description[0:200] + '...'

    class Meta:
        ordering = ('date', 'title')
        abstract = True


class Event(BaseEvent):
    slug = SlugField('slug', editable=False)
    artists = ManyToManyField(Artist, verbose_name='artistas', related_name='events', blank=True)
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True)
    created_by = ForeignKey(
        User, on_delete=CASCADE, editable=False, blank=False, null=True, verbose_name='creado por', related_name='created_events'
    )
    modified_by = ForeignKey(
        User, on_delete=CASCADE, blank=False, null=True, verbose_name='actualizado por', related_name='modified_events'
    )

    def get_absolute_url(self):
        return reverse(
            'events-event_detail',
            kwargs={'year': self.date.year, 'month': self.date.month, 'day': self.date.day, 'event_slug': self.slug},
        )

    def save(self, *args, **kwargs):
        from django.template.defaultfilters import slugify

        self.slug = slugify(self.title)
        super(Event, self).save(*args, **kwargs)

    class Meta:
        unique_together = ('date', 'slug')
        verbose_name = 'evento'
        verbose_name_plural = 'eventos'


class Activity(BaseEvent):
    """
    Activities are special events having also attendance info, attendants can enter in only not closed activities.
    """
    closed = BooleanField('cerrada', default=False)

    class Meta:
        verbose_name = 'actividad'
        verbose_name_plural = 'actividades'


class Attendant(Model):
    """
    An attendant to an activity, can be any person related or not with a subscriber
    """
    activity = ForeignKey(Activity, on_delete=CASCADE)
    name = CharField(u'nombre', max_length=255)
    email = EmailField()
    is_subscriber = BooleanField(u'suscriptor', default=False)
    subscriber = ForeignKey(Subscriber, on_delete=CASCADE, null=True)

    class Meta:
        verbose_name = 'inscripto'
