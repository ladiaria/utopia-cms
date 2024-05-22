# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import (
    Model, FileField, DateTimeField, CharField, PositiveIntegerField, SlugField, BooleanField, TextField
)
from django.utils import timezone


class Audio(Model):
    file = FileField('audio', upload_to='audiologue')
    title = CharField('título', max_length=255)
    slug = SlugField('slug', null=True, blank=True, editable=False)
    caption = CharField('pie', max_length=255, null=True, blank=True)
    byline = CharField('autor/es', max_length=255, null=True, blank=True)
    description = TextField('descripción', null=True, blank=True)
    date_uploaded = DateTimeField('fecha de subida', null=True, blank=True, auto_now_add=True, editable=False)
    times_viewed = PositiveIntegerField('visto', default=0, editable=False)
    is_public = BooleanField('público', default=True)

    class Meta:
        ordering = ('-date_uploaded',)

    def save(self):
        if not self.id:
            self.date_uploaded = timezone.now()
        super(Audio, self).save()

    def __str__(self):
        if self.title:
            return self.title
        else:
            return 'Audio #%i' % self.id
