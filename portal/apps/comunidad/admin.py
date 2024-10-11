# -*- coding: utf-8 -*-
from django.contrib.admin import site, ModelAdmin, TabularInline

from .models import SubscriberArticle, Circuito, Socio, Beneficio, Registro, Url as ComunidadUrl, Recommendation


class CircuitoAdmin(ModelAdmin):
    list_display = ('name',)


class SocioAdmin(ModelAdmin):
    raw_id_fields = ('user',)


class RegistroAdmin(ModelAdmin):
    change_form_template = 'comunidad/admin/registro/change_form.html'

    raw_id_fields = ('subscriber',)
    list_display = ('id', 'subscriber', 'subscriber_email', 'benefit', 'issued', 'used', 'qr_code_small')
    readonly_fields = ('qr_code_image', 'issued')
    list_filter = ('benefit',)
    search_fields = ('subscriber__user__email', 'benefit__slug')

    def qr_code_small(self, obj):
        if obj and obj.pk:
            return obj.qr_code_image(size=60)  # TODO: make a setting to adjust the size as needed
        else:
            return "Save the object to see the QR code"
    qr_code_small.short_description = 'QR'

    def qr_code_image(self, obj):
        if obj and obj.pk:
            return obj.qr_code_image(size=150)  # Larger size for detail view
        else:
            return "Save the object to see the QR code"
    qr_code_image.short_description = 'QR Code'


class BeneficioAdmin(ModelAdmin):
    list_display = ('name', 'circuit', 'slug', 'limit', 'quota')
    list_filter = ('circuit',)


class ComunidadUrlAdmin(ModelAdmin):
    list_display = ('url',)
    search_fields = ('url',)


class UrlInline(TabularInline):
    model = Recommendation.urls.through


class RecommendationAdmin(ModelAdmin):
    raw_id_fields = ('article',)
    list_display = ('name', 'comment', 'url_list', 'article')
    fields = ('name', 'comment', 'article')
    search_fields = ('name', 'comment')
    inlines = (UrlInline,)


site.register(SubscriberArticle)
site.register(Beneficio, BeneficioAdmin)
site.register(Circuito, CircuitoAdmin)
site.register(Socio, SocioAdmin)
site.register(Registro, RegistroAdmin)
site.register(ComunidadUrl, ComunidadUrlAdmin)
site.register(Recommendation, RecommendationAdmin)
