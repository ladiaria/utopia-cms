# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.db.models.fields.related import ForeignKey
from django.db.models.fields import DateTimeField

from updown.fields import RatingField
from core.models import ArticleBase, Article
from cartelera.models import EventoBase
from thedaily.models import Subscriber


class SubscriberArticle(ArticleBase):
    rating = RatingField(can_change_vote=True)
    is_suscriber_article = True

    @staticmethod
    def top_articles():
        desde = datetime.now() - timedelta(days=15)
        return SubscriberArticle.objects.get_query_set().filter(
            date_published__gt=desde)[:3]

    def __unicode__(self):
        return self.headline + ' ( por ' + str(self.created_by) + ' )'

    def save(self, *args, **kwargs):
        self.type = self.COMUNIDAD
        if not self.slug:
            self.slug = slugify(self.headline)
        super(SubscriberArticle, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('comunidad_article_detail', (), {'slug': self.slug})


class SubscriberEvento(EventoBase):
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True)
    created_by = ForeignKey(
        User, verbose_name=u'creado por', related_name='eventos_creados',
        editable=False, blank=False, null=True)

    is_suscriber_evento = True

    def __unicode__(self):
        return self.title + ' ( por ' + str(self.created_by) + ' )'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(SubscriberEvento, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('comunidad_evento_detail', (), {'slug': self.slug})


class TopUser(models.Model):
    user = models.ForeignKey(User)
    points = models.IntegerField()
    date_created = DateTimeField(u'fecha de calculo', auto_now_add=True)
    type = models.CharField(
        max_length=20, choices=[
            ('WEEK', 'WEEK'), ('MONTH', 'MONTH'), ('YEAR', 'YEAR')])


class Circuito(models.Model):
    name = models.CharField('nombre', max_length=64)

    def __unicode__(self):
        return self.name


class Socio(models.Model):
    user = models.OneToOneField(
        User, verbose_name=u'usuario', related_name=u'socio')
    circuits = models.ManyToManyField(Circuito, verbose_name=u'circuitos')

    def __unicode__(self):
        return self.user.username


class Beneficio(models.Model):
    name = models.CharField('nombre', max_length=255)
    circuit = models.ForeignKey(
        Circuito, verbose_name=u'circuito', related_name=u'beneficios')
    limit = models.PositiveIntegerField('cupo general', null=True, blank=True)
    quota = models.PositiveIntegerField('cupo por suscriptor', default=1)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'circuit')


class Registro(models.Model):
    subscriber = models.ForeignKey(Subscriber, verbose_name=u'suscriptor')
    benefit = models.ForeignKey(Beneficio, verbose_name='beneficio')
    used = models.DateTimeField(auto_now_add=True, verbose_name='utilizado')

    def subscriber_email(self):
        return self.subscriber.user.email


class Url(models.Model):
    url = models.URLField(unique=True)

    def __unicode__(self):
        return self.url


class Recommendation(models.Model):
    """
    Primary useful for a chrome extension
    """
    name = models.CharField('nombre', max_length=128, unique=True)
    urls = models.ManyToManyField(Url)
    comment = models.TextField('comentario')
    article = models.ForeignKey(Article, null=True, blank=True)

    def url_list(self):
        return u'<br/>'.join(self.urls.values_list('url', flat=True))

    url_list.allow_tags = True
