# -*- coding: utf-8 -*-

from django.db import models

from thedaily.models import Subscriber, alphanumeric


class Serie(models.Model):
    serie = models.CharField(unique=True, max_length=3)
    min_new_voter = models.PositiveIntegerField(null=True)

    def __unicode__(self):
        return self.serie


class Suscripcion(models.Model):
    subscriber = models.ForeignKey(Subscriber, unique=True)
    credencial_numero = models.PositiveIntegerField(verbose_name='número')
    credencial_serie = models.ForeignKey(
        Serie, verbose_name='serie', related_name='suscripciones')

    def __unicode__(self):
        return u'%s: %s-%d' % (
            self.subscriber, self.credencial_serie, self.credencial_numero)

    def email(self):
        return self.subscriber.user_email

    def user_status(self):
        return 'active' if self.subscriber.user.is_active else 'inactive'

    def is_subscriber(self):
        return self.subscriber.is_subscriber()

    def customer_id(self):
        return self.subscriber.costumer_id
    customer_id.short_description = u'ID en SS'

    class Meta:
        verbose_name_plural = 'suscripciones'
        unique_together = ('credencial_numero', 'credencial_serie')


class Attribution(models.Model):
    name = models.CharField(max_length=255, validators=[alphanumeric])
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    amount = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = u'colaboración'
        verbose_name_plural = 'colaboraciones'
