# -*- coding: utf-8 -*-
from django.utils import timezone

from thedaily.models import SentMail, SubscriberEvent


# WARNING: a change in this variables should be also made in database rows already inserted.
SUBJ_FREE_ARTICLES_LIMIT = u'Usuario alcanza limite de articulos gratis'
SUBJ_MAIL_FREE_ARTICLES_LIMIT = u'Correo por limite de articulos gratis'


def limited_free_article_mail(user):
    """
    if user is authenticated checks if it has to send the free articles limit reach.
    See also automatic_mail module
    """
    if user.is_authenticated():
        subject = SUBJ_FREE_ARTICLES_LIMIT
        send_mail = False
        try:
            event = SubscriberEvent.objects.filter(
                subscriber=user.subscriber, description=subject).latest('date_occurred')
            if not sent_recently(event):
                send_mail = True
        except SubscriberEvent.DoesNotExist:
            send_mail = True
        if send_mail and user.subscriber.allow_promotions:
            SubscriberEvent.objects.create(subscriber=user.subscriber, description=subject)
            # A management command will look at this table and send an email to the subscriber


def sent_recently(event):
    """
    An event (SubscriberEvent) is considered to occurr recently if it already ocurred this month
    returns a boolean value
    """
    now = timezone.now()
    recently = event.date_occurred.year == now.year and event.date_occurred.month == now.month
    return recently
