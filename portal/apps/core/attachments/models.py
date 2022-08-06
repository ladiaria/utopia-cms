# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Model, ForeignKey, FileField, CharField, TextField, BooleanField, DateTimeField

from core.models import Article


class Attachment(Model):
    article = ForeignKey(Article, verbose_name=u'artículo', related_name='attachments')
    file = FileField(u'archivo', upload_to='attachments')
    name = CharField(u'nombre', max_length=50)
    description = TextField(u'descripción', blank=True, null=True)
    is_image = BooleanField(u'es imagen', default=False, editable=False)
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True, editable=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from PIL import Image

        try:
            ifile = Image.open(self.file)
            self.is_image = True
        except Exception:
            self.is_image = False
        super(Attachment, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'adjunto'
        verbose_name_plural = u'adjuntos'
