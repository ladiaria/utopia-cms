# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db.models import Model, ForeignKey, CharField, TextField, DateTimeField, permalink


class Contribution(Model):
    user = ForeignKey(User, verbose_name='usuario', editable=False, related_name='contributions')
    headline = CharField('título', max_length=100)
    body = TextField('cuerpo')
    date_created = DateTimeField('fecha de creación', auto_now_add=True, editable=False)

    def __str__(self):
        return self.headline

    @permalink
    def get_absolute_url(self):
        return '/admin/generator/contribution/%i/' % self.id

    class Meta:
        verbose_name = 'contribución'
        verbose_name_plural = 'contribuciones'
