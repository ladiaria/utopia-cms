# -*- coding: utf-8 -*-
from django.db.models import (
    Model, FileField, DateTimeField, CharField, PositiveIntegerField, SlugField, BooleanField, TextField
)


# in case a pool by year is needed, also a one-time script to update the file paths is provided
"""
import os
def audio_upload_path(instance, filename):
    # Use the year of date_uploaded for the upload path
    year = instance.date_uploaded.year
    return os.path.join('audiologue', str(year), filename)
class Audio(Model):
    file = FileField('audio', upload_to=audio_upload_path)  # Updated upload_to
"""


class Audio(Model):
    # TODO: date_uploaded should be required
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

    def __str__(self):
        if self.title:
            return self.title
        else:
            return 'Audio #%i' % self.id
