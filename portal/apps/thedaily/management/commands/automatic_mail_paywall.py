# -*- coding: utf-8 -*-
"""
"Out of credits" notification emails, how it works:

TODO: translate to english

1. Disparador:

El usuario, estando logueado, consume todos sus créditos gratuitos. Al consumir el último, se ejecuta la funcion
thedaily.email_logic.limited_free_article_mail (TODO: nombrarla de mejor manera) que registra un evento con:
description=DESC_FREE_ARTICLES_LIMIT (No se inserta más de uno x usuario en un mismo mes)

2. Se ejecuta este comando todos los días vía cron:

Este comando toma los eventos del punto anterior creados "ayer", y para cada uno de ellos verifica que el usuario
relacionado no posea un "SentMail" con el subject=SUBJ_MAIL_FREE_ARTICLES_LIMIT enviado este mes.
Si se da esa condicion, se le envía al usuario un email informándole que consumió todos sus créditos y se registra
dicho envío para no ser repetitivos y que durante el transcurso del mes no haya chance de enviarle otro mail identico.
"""


from datetime import time
from time import sleep
import logging
import smtplib

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.timezone import datetime, timedelta, make_aware

from thedaily.models import SentMail, SubscriberEvent
from thedaily.email_logic import DESC_FREE_ARTICLES_LIMIT, whitelisted, sent_recently
from thedaily.tasks import notifications_template_dir, send_notification
from thedaily.utils import get_notification_subjects


# WARNING: A change on this variable should also be made in database rows already inserted.
SUBJ_MAIL_FREE_ARTICLES_LIMIT = 'Correo por limite de articulos gratis'

log = logging.getLogger(__name__)
log.addHandler(logging.FileHandler(filename=settings.THEDAILY_AUTOMATIC_MAIL_LOGFILE))
log.setLevel(logging.INFO)


def send_message(user):
    template_name = "signup_wall.html"
    send_notification(
        user,
        f"{notifications_template_dir}{template_name}",
        get_notification_subjects()[template_name],
        {
            "notifications_signup_base": f"{notifications_template_dir}signup.html",
            "signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS,
        },
    )


def send_paywall_mails(disable_notifications, delay=0, debug=False):
    now = timezone.now()
    yesterday = now.date() - timedelta(1)
    events = SubscriberEvent.objects.filter(
        date_occurred__range=(
            make_aware(datetime.combine(yesterday, time.min)),
            make_aware(datetime.combine(yesterday, time.max)),
        ),
        description=DESC_FREE_ARTICLES_LIMIT,
    )
    if debug:
        print(f"DEBUG: automatic_mail_paywall, #events: {len(events)}")
    subscribers = []
    # in SubscriberEvent could be more than 1 row per subscriber because a race condition at saving the row,
    # the list 'subscribers' is used for filtering duplicates
    for e in events:
        subscriber = e.subscriber
        # send only 1 mail per non-subscriber
        if not (subscriber.id in subscribers or subscriber.is_subscriber_any()):
            subscribers.append(subscriber.id)
            send_mail = False
            # filter mail already sent this month
            try:
                mail = SentMail.objects.filter(
                    subscriber=subscriber, subject=SUBJ_MAIL_FREE_ARTICLES_LIMIT
                ).latest('date_sent')
                if not sent_recently(mail, 'date_sent'):
                    send_mail = True
            except SentMail.DoesNotExist:
                send_mail = True

            user = subscriber.user
            if (not disable_notifications or whitelisted(user.email)) and subscriber.allow_promotions and send_mail:
                try:
                    send_message(user)
                except smtplib.SMTPRecipientsRefused:
                    log.error("%s Email refused for subscriber %s\t%s" % (now, subscriber.id, user.email))
                else:
                    SentMail.objects.create(subscriber=subscriber, subject=SUBJ_MAIL_FREE_ARTICLES_LIMIT)
                    if delay:
                        sleep(delay)
            elif send_mail:
                log.info('Notificación deshabilitada: ' + user.email)


class Command(BaseCommand):
    help = 'Sends email notifications to users that reached paywall. Run only once per day to avoid dupe delivery'

    def add_arguments(self, parser):
        parser.add_argument(
            '--disable-notifications',
            action='store_true',
            default=False,
            dest='disable_notifications',
            help='Disable email delivery if email is not whitelisted, useful in testing',
        )
        parser.add_argument(
            '--delay',
            action='store',
            default=0,
            type=float,
            dest='delay',
            help='Seconds to wait after a successful delivery, e.g. to wait 500 miliseconds: --delay=0.5',
        )

    def handle(self, *args, **options):
        send_paywall_mails(options.get('disable_notifications'), options.get("delay"), options.get("verbosity") > 1)
