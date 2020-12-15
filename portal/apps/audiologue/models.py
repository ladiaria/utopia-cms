# -*- coding: utf-8 -*-
from django.db.models import (Model, FileField, DateTimeField, CharField,
    PositiveIntegerField, SlugField, BooleanField, TextField, OneToOneField)

from datetime import datetime


class Audio(Model):
    file = FileField(u'audio', upload_to='audiologue')
    title = CharField(u'título', max_length=255)
    slug = SlugField(u'slug', null=True, blank=True, editable=False)
    caption = CharField(u'pie', max_length=255, null=True, blank=True)
    byline = CharField(u'autor/es', max_length=255, null=True, blank=True)
    description = TextField(u'descripción', null=True, blank=True)
    date_uploaded = DateTimeField(u'fecha de subida', null=True, blank=True,
        auto_now_add=True, editable=False)
    times_viewed = PositiveIntegerField(u'visto', default=0, editable=False)
    is_public = BooleanField(u'público', default=True)

    def save(self):
        if not self.id:
            self.date_uploaded = datetime.now()
        super(Audio, self).save()

    def __unicode__(self):
        if self.title:
            return self.title
        else:
            return u'Audio #%i' % self.id
