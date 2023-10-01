# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.admin import ModelAdmin, SimpleListFilter, site

from apps.admin import ReadOnlyModelAdmin
from dashboard.models import NewsletterDelivery, AudioStatistics


class NLNameFilter(SimpleListFilter):
    title = 'newsletter name'
    parameter_name = 'newsletter_name'

    def lookups(self, request, model_admin):
        return [
            (nld.newsletter_name, nld.get_newsletter_name()) for nld in NewsletterDelivery.objects.raw(
                'SELECT id,newsletter_name FROM %s GROUP BY newsletter_name' % NewsletterDelivery._meta.db_table
            )
        ]

    def queryset(self, request, queryset):
        newsletter_name = self.value()
        return queryset.filter(newsletter_name=newsletter_name) if newsletter_name else queryset


class NewsletterDeliveryAdmin(ModelAdmin):
    list_display = ('delivery_date_short', 'get_newsletter_name', 'user_stats', 'subscriber_stats', 'total_stats')
    readonly_fields = (
        'delivery_date',
        'newsletter_name',
        'user_sent',
        'subscriber_sent',
        'user_refused',
        'subscriber_refused',
        'user_opened',
        'subscriber_opened',
        'user_bounces',
        'subscriber_bounces',
    )
    list_filter = (NLNameFilter, )
    date_hierarchy = 'delivery_date'


class AudioStatisticsAdmin(ReadOnlyModelAdmin):
    # TODO: audio linked to audio asset
    list_display = ['audio', 'subscriber', 'percentage', 'amp_click']
    list_filter = ['percentage']


site.register(NewsletterDelivery, NewsletterDeliveryAdmin)
site.register(AudioStatistics, AudioStatisticsAdmin)
