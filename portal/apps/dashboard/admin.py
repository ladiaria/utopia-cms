# -*- coding: utf-8 -*-

from django.contrib.admin import ModelAdmin, site
from dashboard.models import NewsletterDelivery, AudioStatistics


class NewsletterDeliveryAdmin(ModelAdmin):
    list_display = readonly_fields = (
        'delivery_date', 'newsletter_name', 'user_sent', 'subscriber_sent', 'user_refused', 'subscriber_refused',
        'user_opened', 'subscriber_opened', 'user_bounces', 'subscriber_bounces')
    list_filter = ('newsletter_name', )
    date_hierarchy = 'delivery_date'


class AudioStatisticsAdmin(ModelAdmin):
    list_display = ['audio', 'subscriber', 'percentage']
    raw_id_fields = ['audio', 'subscriber']


site.register(NewsletterDelivery, NewsletterDeliveryAdmin)
site.register(AudioStatistics, AudioStatisticsAdmin)
