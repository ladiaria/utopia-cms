# -*- coding: utf-8 -*-
from django.db.models import (
    CharField, Model, DateField, ForeignKey, PositiveIntegerField, PositiveSmallIntegerField, BooleanField)

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

    class Meta:
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
