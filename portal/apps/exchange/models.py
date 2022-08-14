# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from builtins import str

from django.db.models import Model, CharField, ForeignKey, DateField, FloatField, ImageField, SlugField
from django.template.defaultfilters import slugify


def flag_upload_to(instance, filename):
    return 'exchange/%s.%s' % (slugify(instance.name), filename.split('.')[-1])


class Currency(Model):
    name = CharField('moneda', max_length=50, unique=True)
    slug = SlugField('slug', unique=True)
    symbol = CharField('símbolo', max_length=4)
    flag = ImageField(
        'bandera', upload_to=flag_upload_to, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'moneda'
        verbose_name_plural = 'monedas'


class Exchange(Model):
    currency = ForeignKey(Currency, blank=False, null=False)
    date = DateField(u'fecha', auto_now_add=True)
    buy = FloatField(u'compra')
    sale = FloatField(u'venta')

    def __str__(self):
        return '%s %s' % (self.currency.name, str(self.date))

    class Meta:
        verbose_name = 'cotización'
        verbose_name_plural = 'cotizaciones'
        unique_together = ('currency', 'date')
        get_latest_by = 'date'
