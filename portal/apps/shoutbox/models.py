# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db.models import CASCADE
from django.db.models import Model, ForeignKey, CharField, DateTimeField


class Shout(Model):
    user = ForeignKey(User, on_delete=CASCADE, verbose_name=u'usuario', related_name='shouts')
    message = CharField(u'mensaje', max_length=140)
    post_date = DateTimeField(u'fecha', auto_now_add=True)

    def __str__(self):
        return self.message

    def save(self, *args, **kwargs):
        from django.core.cache import cache

        cache.delete('shouts')
        super(Shout, self).save(*args, **kwargs)

    class Meta:
        get_latest_by = 'post_date'
        ordering = ('-post_date',)
        verbose_name = u'mensaje'
        verbose_name_plural = u'mensajes'


def get_last_shouts(how_many=5):
    shouts_query = list(Shout.objects.all().order_by('-post_date')[:how_many])
    shouts_query.reverse()
    return shouts_query
