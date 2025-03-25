# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils import timezone

from thedaily.models import SubscriberEvent


# WARNING: A change on this variable should also be made in database rows already inserted.
DESC_FREE_ARTICLES_LIMIT = 'Usuario alcanza limite de articulos gratis'
notifications_whitelist = getattr(settings, 'THEDAILY_NOTIFICATIONS_WHITELIST', [])


def whitelisted(email_addr):
    """
    Useful in testing, to avoid send unwanted emails by mistake and send mail only to whitelisted emails.
    """
    return email_addr in notifications_whitelist


def sent_recently(instance, field_name):
    """
    An instance of any object that has an attribute named with the field name given, is considered "sent recently" iff:
    - the value of the field is within the current month.
    returns a boolean value
    """
    now = timezone.now()
    return (
        getattr(instance, field_name, None).year == now.year and getattr(instance, field_name, None).month == now.month
    )


def limited_free_article_mail(user):
    """
    Register the event of "out of free credits" if user is authenticated
    """
    if user.is_authenticated:
        send_mail = False
        try:
            event = SubscriberEvent.objects.filter(
                subscriber=user.subscriber, description=DESC_FREE_ARTICLES_LIMIT
            ).latest('date_occurred')
            if not sent_recently(event, 'date_occurred'):
                send_mail = True
        except SubscriberEvent.DoesNotExist:
            send_mail = True
        if send_mail and user.subscriber.allow_promotions:
            SubscriberEvent.objects.create(subscriber=user.subscriber, description=DESC_FREE_ARTICLES_LIMIT)
