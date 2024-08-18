# -*- coding: utf-8 -*-

from django.utils import timezone

from thedaily.models import SubscriberEvent


# WARNING: A change on this variable should also be made in database rows already inserted.
DESC_FREE_ARTICLES_LIMIT = 'Usuario alcanza limite de articulos gratis'


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
            if not sent_recently(event):
                send_mail = True
        except SubscriberEvent.DoesNotExist:
            send_mail = True
        if send_mail and user.subscriber.allow_promotions:
            SubscriberEvent.objects.create(subscriber=user.subscriber, description=DESC_FREE_ARTICLES_LIMIT)


def sent_recently(event):
    """
    An event (SubscriberEvent) is considered to occurr recently if it already ocurred this month
    returns a boolean value
    """
    now = timezone.now()
    recently = event.date_occurred.year == now.year and event.date_occurred.month == now.month
    return recently
