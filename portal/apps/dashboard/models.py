# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.models import (
    CharField, Model, DateField, ForeignKey, PositiveIntegerField, PositiveSmallIntegerField, BooleanField
)
from django.utils.formats import date_format

from core.models import Publication, Category
from audiologue.models import Audio
from thedaily.models import Subscriber


class NewsletterDelivery(Model):
    """
    Store newsletter delivery stats such as how many emails were sent, which
    users had opened it and what was their subscriber condition when the open
    event was triggered in Google Analytics.
    """
    delivery_date = DateField(auto_now_add=True)
    newsletter_name = CharField(max_length=64)
    user_sent = PositiveIntegerField(blank=True, null=True)
    subscriber_sent = PositiveIntegerField(blank=True, null=True)
    user_refused = PositiveIntegerField(blank=True, null=True)
    subscriber_refused = PositiveIntegerField(blank=True, null=True)
    user_opened = PositiveIntegerField(blank=True, null=True)
    subscriber_opened = PositiveIntegerField(blank=True, null=True)
    user_bounces = PositiveIntegerField(blank=True, null=True)
    subscriber_bounces = PositiveIntegerField(blank=True, null=True)

    def delivery_date_short(self):
        return date_format(self.delivery_date, format=settings.SHORT_DATE_FORMAT, use_l10n=True)

    delivery_date_short.short_description = u'delivery date'

    def get_newsletter_name(self):
        try:
            return Publication.objects.get(newsletter_campaign=self.newsletter_name).newsletter_name
        except Publication.DoesNotExist:
            return Category.objects.get(slug=self.newsletter_name).name

    get_newsletter_name.short_description = u'newsletter'

    class Meta:
        app_label = 'dashboard'
        unique_together = ('delivery_date', 'newsletter_name')


class AudioStatistics(Model):
    """
    Save audio usage statistics for each user.
    """
    subscriber = ForeignKey(Subscriber)
    audio = ForeignKey(Audio)
    percentage = PositiveSmallIntegerField(null=True, blank=True)
    amp_click = BooleanField(default=False)

    class Meta:
        unique_together = ('subscriber', 'audio')
