# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.admin import site, ModelAdmin, TabularInline

from .models import SubscriberArticle, Circuito, Socio, Beneficio, Registro, Url, Recommendation


class CircuitoAdmin(ModelAdmin):
    list_display = ('name', )


class SocioAdmin(ModelAdmin):
    raw_id_fields = ('user', )


class RegistroAdmin(ModelAdmin):
    raw_id_fields = ('subscriber', )
    list_display = ('subscriber', 'subscriber_email', 'benefit', 'used')
    list_filter = ('benefit', )


class BeneficioAdmin(ModelAdmin):
    list_display = ('name', 'circuit', 'limit', 'quota')
    list_filter = ('circuit', )


class UrlAdmin(ModelAdmin):
    list_display = ('url', )
    search_fields = ('url', )


class UrlInline(TabularInline):
    model = Recommendation.urls.through


class RecommendationAdmin(ModelAdmin):
    raw_id_fields = ('article', )
    list_display = ('name', 'comment', 'url_list', 'article')
    fields = ('name', 'comment', 'article')
    search_fields = ('name', 'comment')
    inlines = (UrlInline, )


site.register(SubscriberArticle)
site.register(Beneficio, BeneficioAdmin)
site.register(Circuito, CircuitoAdmin)
site.register(Socio, SocioAdmin)
site.register(Registro, RegistroAdmin)
site.register(Url, UrlAdmin)
site.register(Recommendation, RecommendationAdmin)
