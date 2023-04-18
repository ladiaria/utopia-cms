# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db.models import CASCADE
from django.db.models import Model, ForeignKey, CharField, TextField, DateTimeField

# from django.db.models import permalink DEPRECATED


class Contribution(Model):
    user = ForeignKey(User, on_delete=CASCADE, verbose_name='usuario', editable=False, related_name='contributions')
    headline = CharField('título', max_length=100)
    body = TextField('cuerpo')
    date_created = DateTimeField('fecha de creación', auto_now_add=True, editable=False)

    def __str__(self):
        return self.headline

    # @permalink DEPRECATED! What to do?
    def get_absolute_url(self):
        return reverse("admin:generator_contribution_change", args=[self.id])
        # previamente: '/admin/generator/contribution/%i/' % self.id

    class Meta:
        verbose_name = 'contribución'
        verbose_name_plural = 'contribuciones'
