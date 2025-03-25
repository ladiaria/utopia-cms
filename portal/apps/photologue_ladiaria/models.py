# -*- coding: utf-8 -*-

import os
from PIL import Image

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from photologue.models import Photo, PhotoSize, get_storage_path


class Agency(models.Model):
    name = models.CharField('nombre', max_length=50, unique=True)
    info = models.EmailField('email', blank=True, null=True)
    date_created = models.DateTimeField('fecha de creación', auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        get_latest_by = 'date_created'
        ordering = ['name']
        verbose_name = 'agencia'
        verbose_name_plural = 'agencias'


class Photographer(models.Model):
    name = models.CharField('nombre', max_length=50, unique=True)
    email = models.EmailField(blank=True, null=True)
    date_created = models.DateTimeField('fecha de creación', auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        get_latest_by = 'date_created'
        ordering = ['name']
        verbose_name = 'fotógrafo'
        verbose_name_plural = 'fotógrafos'


class PhotoExtended(models.Model):
    FOTO = 'f'
    ILUSTRACION = 'i'
    TYPE = (
        (FOTO, 'Foto'),
        (ILUSTRACION, 'Ilustración'),
    )
    type = models.CharField('tipo', max_length=1, choices=TYPE, default=FOTO)
    image = models.OneToOneField(Photo, on_delete=models.CASCADE, related_name='extended')
    focuspoint_x = models.CharField('punto de foco horizontal (x)', max_length=10, default=0, help_text='')
    focuspoint_y = models.CharField('punto de foco vertical (y)', max_length=10, default=0, help_text='')
    radius_length = models.SmallIntegerField(
        'radio', blank=True, null=True, help_text='mitad del lado del cuadrado para recorte (pixeles)'
    )
    square_version = models.ImageField(
        'versión cuadrada', upload_to=get_storage_path, max_length=255, blank=True, null=True
    )
    weight = models.SmallIntegerField(
        'orden de la imagen en la galería', default=0, help_text='el número más bajo se muestra primero.'
    )
    photographer = models.ForeignKey(
        Photographer, on_delete=models.CASCADE, verbose_name='autor', related_name='photos', blank=True, null=True
    )
    agency = models.ForeignKey(
        Agency, on_delete=models.CASCADE, verbose_name='agencia', related_name='photos', blank=True, null=True
    )

    class Meta:
        verbose_name = 'configuración extra'
        verbose_name_plural = 'configuraciones extra'

    def __str__(self):
        return self.image.title

    def image_file_exists(self):
        try:
            result = bool(self.image.image.file)
        except IOError:
            result = False
        return result

    @property
    def width(self):
        return Image.open(self.image.image.file).width

    @property
    def height(self):
        return Image.open(self.image.image.file).height

    @property
    def is_landscape(self):
        if self.image_file_exists():
            width, height = Image.open(self.image.image.file).size
            return width > height
        else:
            return True

    @property
    def is_portrait(self):
        return not self.is_landscape

    def save(self, *args, **kwargs):
        # if square box given then generate the square version, else remove it
        if all([getattr(self, attr) is not None for attr in ('focuspoint_x', 'focuspoint_y', 'radius_length')]):
            try:
                im = Image.open(self.image.image.path)

                # TODO: explain this commented line or remove it if it does not make any sense
                # box = (left, up, x, y)is_portrait

                square_box = (
                    int(self.focuspoint_x) - self.radius_length,
                    int(self.focuspoint_y) - self.radius_length,
                    int(self.focuspoint_x) + self.radius_length,
                    int(self.focuspoint_y) + self.radius_length,
                )

                self.square_version = os.path.join(
                    os.path.dirname(self.image.image.path), self.image._get_filename_for_size(PhotoSize(name='square'))
                )
                im.crop(square_box).save(self.square_version.path)
            except IOError:
                pass
        else:
            self.square_version = None
        super().save(*args, **kwargs)

    def get_square_version_filename(self):
        return os.path.basename(self.square_version.path)


@receiver(post_save, sender=Photo)
def photo_post_save_handler(sender, **kwargs):
    instance = kwargs['instance']
    if not hasattr(instance, 'extended'):
        PhotoExtended.objects.create(image=instance)
