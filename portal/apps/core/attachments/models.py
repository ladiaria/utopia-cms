# -*- coding: utf-8 -*-

from django.db.models import CASCADE
from django.db.models import Model, ForeignKey, FileField, CharField, TextField, BooleanField, DateTimeField

from core.models import Article


class Attachment(Model):
    article = ForeignKey(Article, on_delete=CASCADE, verbose_name='artículo', related_name='attachments')
    file = FileField('archivo', upload_to='attachments')
    name = CharField('nombre', max_length=50)
    description = TextField('descripción', blank=True, null=True)
    is_image = BooleanField('es imagen', default=False, editable=False)
    date_created = DateTimeField('fecha de creación', auto_now_add=True, editable=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from PIL import Image

        try:
            Image.open(self.file)
            self.is_image = True
        except Exception:
            self.is_image = False
        super(Attachment, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'adjunto'
        verbose_name_plural = 'adjuntos'
