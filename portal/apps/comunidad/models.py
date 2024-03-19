# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.fields.related import ForeignKey
from django.db.models.fields import DateTimeField
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User

from updown.fields import RatingField
from core.models import ArticleBase, Article
from cartelera.models import EventoBase
from thedaily.models import Subscriber


class SubscriberArticle(ArticleBase):
    rating = RatingField(can_change_vote=True)
    is_suscriber_article = True

    @staticmethod
    def top_articles():
        desde = timezone.now() - timedelta(days=15)
        return SubscriberArticle.objects.get_queryset().filter(date_published__gt=desde)[:3]

    def __str__(self):
        return self.headline + ' ( por ' + str(self.created_by) + ' )'

    def save(self, *args, **kwargs):
        self.type = settings.CORE_COMUNIDAD_ARTICLE
        if not self.slug:
            self.slug = slugify(self.headline)
        super(SubscriberArticle, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('comunidad_article_detail', kwargs={'slug': self.slug})


class SubscriberEvento(EventoBase):
    date_created = DateTimeField('fecha de creación', auto_now_add=True)
    created_by = ForeignKey(
        User,
        verbose_name='creado por',
        related_name='eventos_creados',
        editable=False,
        blank=False,
        null=True,
        on_delete=models.CASCADE,
    )

    is_suscriber_evento = True

    def __str__(self):
        return self.title + ' ( por ' + str(self.created_by) + ' )'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(SubscriberEvento, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('comunidad_evento_detail', kwargs={'slug': self.slug})


class TopUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.IntegerField()
    date_created = DateTimeField('fecha de calculo', auto_now_add=True)
    type = models.CharField(max_length=20, choices=[('WEEK', 'WEEK'), ('MONTH', 'MONTH'), ('YEAR', 'YEAR')])


class Circuito(models.Model):
    name = models.CharField('nombre', max_length=64)

    def __str__(self):
        return self.name


class Socio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='usuario', related_name='socio')
    circuits = models.ManyToManyField(Circuito, verbose_name='circuitos')

    def __str__(self):
        return self.user.username


class Beneficio(models.Model):
    name = models.CharField('nombre', max_length=255)
    circuit = models.ForeignKey(Circuito, on_delete=models.CASCADE, verbose_name='circuito', related_name='beneficios')
    limit = models.PositiveIntegerField('cupo general', null=True, blank=True)
    quota = models.PositiveIntegerField('cupo por suscriptor', default=1)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'circuit')


class Registro(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, verbose_name='suscriptor')
    benefit = models.ForeignKey(Beneficio, on_delete=models.CASCADE, verbose_name='beneficio')
    used = models.DateTimeField(auto_now_add=True, verbose_name='utilizado')

    def subscriber_email(self):
        return self.subscriber.user.email


class Url(models.Model):
    url = models.URLField(unique=True)

    def __str__(self):
        return self.url


class Recommendation(models.Model):
    """
    Primary useful for a chrome extension
    """

    name = models.CharField('nombre', max_length=128, unique=True)
    urls = models.ManyToManyField(Url)
    comment = models.TextField('comentario')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, null=True, blank=True)

    def url_list(self):
        return mark_safe('<br>'.join(self.urls.values_list('url', flat=True)))
