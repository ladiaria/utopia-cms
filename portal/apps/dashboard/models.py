# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import reverse
from django.db.models import CASCADE
from django.db.models import (
    CharField, Model, DateField, ForeignKey, PositiveIntegerField, PositiveSmallIntegerField, BooleanField
)
from django.utils.formats import date_format
from django.utils.safestring import mark_safe

from core.models import Publication, Category
from audiologue.models import Audio
from thedaily.models import Subscriber


def nl_delivery_stats_cell(sent, opened, nl_delivery_id=None, nl_delivery_segment=None):
    sent_row, link_open_tag = 'Envíos: %s' % (sent if sent is not None else 'Pendiente'), ""
    if opened is not None and sent and nl_delivery_id and nl_delivery_segment:
        reverse_kwargs = {"nl_delivery_id": nl_delivery_id, "nl_delivery_segment": nl_delivery_segment}
        link_open_tag = (
            '<a href="%s" title="Click to download the subscribers id list in CSV format">' % (
                reverse("nl_open", kwargs=reverse_kwargs)
            )
        )
    opened_row = 'Apertura: %s' % (
        '%s%s%s (%.2f%%)' % (
            link_open_tag,
            opened,
            "</a>" if link_open_tag else "",
            (opened / sent) * 100,
        ) if opened is not None and sent else 'Pendiente',
    )
    return '<br>'.join((sent_row, opened_row))


class NewsletterDelivery(Model):
    """
    Store newsletter delivery stats such as how many emails were sent, which users had opened it and what was their
    subscriber condition when the open event was triggered in Google Analytics.
    """
    delivery_date = DateField(auto_now_add=True)
    newsletter_name = CharField(max_length=64)
    user_sent = PositiveIntegerField(blank=True, null=True)
    subscriber_sent = PositiveIntegerField(blank=True, null=True)
    user_opened = PositiveIntegerField(blank=True, null=True)
    subscriber_opened = PositiveIntegerField(blank=True, null=True)
    user_bounces = PositiveIntegerField(blank=True, null=True)
    subscriber_bounces = PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return "%s stats for '%s' delivered on %s: %s" % (
            self.__class__.__name__,
            self.newsletter_name,
            str(self.delivery_date),
            (self.user_opened, self.subscriber_opened),
        )

    def delivery_date_short(self):
        return date_format(self.delivery_date, format=settings.SHORT_DATE_FORMAT, use_l10n=True)

    delivery_date_short.short_description = 'delivery date'

    def get_newsletter_name(self):
        try:
            p = Publication.objects.get(newsletter_campaign=self.newsletter_name)
            return p.newsletter_name or p.newsletter_campaign
        except Publication.DoesNotExist:
            try:
                return Category.objects.get(slug=self.newsletter_name).name
            except Category.DoesNotExist:
                return self.newsletter_name

    get_newsletter_name.short_description = 'newsletter'

    def user_stats(self):
        return mark_safe(nl_delivery_stats_cell(self.user_sent, self.user_opened, self.id, "user"))

    user_stats.short_description = 'cuenta gratuita'

    def subscriber_stats(self):
        return mark_safe(nl_delivery_stats_cell(self.subscriber_sent, self.subscriber_opened, self.id, "subscriber"))

    subscriber_stats.short_description = 'suscripciones de pago'

    def total_stats(self):
        s_arg = self.user_sent is not None and self.subscriber_sent is not None
        o_arg = self.user_opened is not None and self.subscriber_opened is not None
        return mark_safe(
            nl_delivery_stats_cell(
                ((self.user_sent or 0) + (self.subscriber_sent or 0)) if s_arg else None,
                ((self.user_opened or 0) + (self.subscriber_opened or 0)) if o_arg else None,
            )
        )

    total_stats.short_description = 'total'

    class Meta:
        app_label = 'dashboard'
        unique_together = ('delivery_date', 'newsletter_name')


class AudioStatistics(Model):
    """
    Save audio usage statistics for each user.
    """
    subscriber = ForeignKey(Subscriber, on_delete=CASCADE)
    audio = ForeignKey(Audio, on_delete=CASCADE)
    percentage = PositiveSmallIntegerField(null=True, blank=True)
    amp_click = BooleanField(default=False)

    class Meta:
        unique_together = ('subscriber', 'audio')
