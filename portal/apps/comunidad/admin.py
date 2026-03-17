# -*- coding: utf-8 -*-
import csv

from django.contrib.admin import site, ModelAdmin, TabularInline, SimpleListFilter
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from .models import (
    SubscriberArticle, Circuito, Socio, Beneficio, Registro, RegistroUse,
    Url as ComunidadUrl, Recommendation,
)


class CircuitoAdmin(ModelAdmin):
    list_display = ('name',)


class SocioAdmin(ModelAdmin):
    raw_id_fields = ('user',)


class UsedFilter(SimpleListFilter):
    title = _('Usado')  # The title for the filter
    parameter_name = 'used_null'  # The query parameter for the filter

    def lookups(self, request, model_admin):
        # Defining the filter options
        return (
            ('yes', _('Used')),
            ('no', _('Not Used')),
        )

    def queryset(self, request, queryset):
        # Filtering logic based on the selected filter option
        if self.value() == 'yes':
            return queryset.exclude(used__isnull=True)
        if self.value() == 'no':
            return queryset.filter(used__isnull=True)
        return queryset


def export_registros_csv(modeladmin, request, queryset):
    if not request.user.has_perm('comunidad.export_registro'):
        modeladmin.message_user(request, _("No tenés permiso para exportar registros."))
        return
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="registros.csv"'
    writer = csv.writer(response)
    writer.writerow([
            'ID', 'Hash', 'Subscriber', 'Name', 'Email', 'Phone',
            'Benefit', 'Dependents', 'Notes', 'Issued', 'Used',
        ])
    for r in queryset.select_related('subscriber__user', 'benefit'):
        writer.writerow([
            r.id,
            r.generate_hashed_id(),
            r.subscriber.user.username if r.subscriber else '',
            r.name or '',
            r.subscriber_email() or '',
            r.phone or '',
            r.benefit.name,
            r.dependents if r.dependents is not None else '',
            r.notes or '',
            r.issued,
            r.used or '',
        ])
    return response


export_registros_csv.short_description = _('Exportar registros seleccionados a CSV')


class RegistroUseInline(TabularInline):
    model = RegistroUse
    readonly_fields = ('used_at',)
    extra = 0


class RegistroAdmin(ModelAdmin):
    change_form_template = 'comunidad/admin/registro/change_form.html'

    raw_id_fields = ('subscriber',)
    inlines = [RegistroUseInline]
    list_display = (
        'id', 'hashed_id', 'subscriber', 'name', 'subscriber_email', 'phone',
        'benefit', 'dependents', 'notes', 'issued', 'used', 'qr_code_small',
    )
    readonly_fields = ('qr_code_image', 'hashed_id', 'issued')
    list_filter = ('benefit', UsedFilter)
    search_fields = ('subscriber__user__email', 'email', 'name', 'phone')
    actions = [export_registros_csv]

    def hashed_id(self, obj):
        if obj and obj.pk:
            return obj.generate_hashed_id()
        return '-'

    hashed_id.short_description = 'Hash ID'

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
    list_display = ('name', 'circuit', 'slug', 'limit', 'quota', 'max_uses')
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
