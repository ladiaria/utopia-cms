# -*- coding: utf-8 -*-
from __future__ import division

from django.conf import settings
from django.db.models import (
    CharField, Model, DateField, ForeignKey, PositiveIntegerField, PositiveSmallIntegerField, BooleanField
)
from django.utils.formats import date_format

from core.models import Publication, Category
from audiologue.models import Audio
from thedaily.models import Subscriber


def nl_delivery_stats_cell(sent, opened):
    sent_row = u'Envíos: %s' % (sent if sent is not None else u'Pendiente')
    opened_row = u'Apertura: %s' % (
        (u'%s (%.2f%%)' % (opened, (opened / sent) * 100)) if opened is not None and sent else u'Pendiente'
    )
    return u'<br>'.join((sent_row, opened_row))


class NewsletterDelivery(Model):
    """
    Store newsletter delivery stats such as how many emails were sent, which users had opened it and what was their
    subscriber condition when the open event was triggered in Google Analytics.
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
            p = Publication.objects.get(newsletter_campaign=self.newsletter_name)
            return p.newsletter_name or p.newsletter_campaign
        except Publication.DoesNotExist:
            try:
                return Category.objects.get(slug=self.newsletter_name).name
            except Category.DoesNotExist:
                return self.newsletter_name

    get_newsletter_name.short_description = u'newsletter'

    def user_stats(self):
        return nl_delivery_stats_cell(self.user_sent, self.user_opened)

    user_stats.short_description, user_stats.allow_tags = u'suscripción gratuita', True

    def subscriber_stats(self):
        return nl_delivery_stats_cell(self.subscriber_sent, self.subscriber_opened)

    subscriber_stats.short_description, subscriber_stats.allow_tags = u'suscripciones de pago', True

    def total_stats(self):
        s_arg = self.user_sent is not None and self.subscriber_sent is not None
        o_arg = self.user_opened is not None and self.subscriber_opened is not None
        return nl_delivery_stats_cell(
            ((self.user_sent or 0) + (self.subscriber_sent or 0)) if s_arg else None,
            ((self.user_opened or 0) + (self.subscriber_opened or 0)) if o_arg else None,
        )

    total_stats.short_description, total_stats.allow_tags = u'total', True

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
