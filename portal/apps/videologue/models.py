# -*- coding: utf-8 -*-
import re

from django.db.models import (
    BooleanField, CharField, DateTimeField, FileField, Model, PositiveIntegerField, SlugField, TextField, URLField
)


YT_RE = re.compile(r'(?:v|embed|youtu.be)[=\/]([\w_-]{11})')


class Video(Model):
    file = FileField('Video', upload_to='videologue')
    title = CharField('Título', max_length=255)
    slug = SlugField('Slug', null=True, blank=True, editable=False)
    caption = CharField('Pie', max_length=255, null=True, blank=True)
    byline = CharField('Autor/es', max_length=255, null=True, blank=True)
    description = TextField('Descripción', null=True, blank=True)
    date_uploaded = DateTimeField('Subido', null=True, blank=True, auto_now_add=True, editable=False)
    times_viewed = PositiveIntegerField('Visto', default=0, editable=False)
    is_public = BooleanField('Público', default=True)

    def __str__(self):
        if self.title:
            return self.title
        else:
            return 'Video #%i' % self.id


class YouTubeVideo(Model):
    url = URLField('URL de YouTube', unique=True)
    title = CharField('Título', max_length=50, blank=True, null=True)
    description = TextField('Descripción', blank=True, null=True)
    date_created = DateTimeField('Fecha de creación', auto_now_add=True)
    yt_id = CharField('ID Youtube', max_length=11, blank=True, null=True)

    @staticmethod
    def format_url(yid):
        return f'https://www.youtube.com/watch?v={yid}'

    @property
    def embed_url(self):
        return f'https://www.youtube.com/embed/{self.yt_id}'

    def save(self, *args, **kwargs):
        yid = YT_RE.findall(self.url)[0]
        self.yt_id = yid
        self.url = YouTubeVideo.format_url(yid)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title if self.title else 'Video #%i' % self.id

    class Meta:
        get_latest_by = 'date_created'
        verbose_name = 'Video YouTube'
        verbose_name_plural = 'Videos YouTube'
