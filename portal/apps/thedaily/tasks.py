# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from emails.django import DjangoMessage as Message

from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from libs.utils import smtp_connect
from thedaily.models import SentMail


welcome_email_template = 'notifications/new_subscription%s.html'
welcome_email_sub = u'Tu suscripción %s está activa'


def send_notification(user, email_template, email_subject, extra_context={}):
    extra_context.update(
        {
            'SITE_URL': settings.SITE_URL,
            'URL_SCHEME': settings.URL_SCHEME,
            'site': Site.objects.get_current(),
            'logo_url': settings.HOMEV3_SECONDARY_LOGO,
        }
    )
    msg = Message(
        html=render_to_string(email_template, extra_context),
        mail_to=(user.get_full_name(), user.email),
        subject=email_subject,
        mail_from=(settings.NOTIFICATIONS_FROM_NAME, settings.NOTIFICATIONS_FROM_ADDR1),
    )

    # send using smtp to receive bounces in another mailbox
    s = smtp_connect()
    s.sendmail(settings.NOTIFICATIONS_FROM_MX, [user.email], msg.as_string())
    s.quit()


def notify_digital(user, seller_fullname=None):
    send_notification(
        user,
        welcome_email_template,
        welcome_email_sub % 'digital',
        {'seller_fullname': seller_fullname} if seller_fullname else {},
    )
    SentMail.objects.create(subscriber=user.subscriber, subject="Bienvenida DI")


def notify_paper(user, seller_fullname=None):
    extra_context = {'seller_fullname': seller_fullname} if seller_fullname else {}
    send_notification(
        user, welcome_email_template % '_PAPYDIM', welcome_email_sub % u'a la edición papel', extra_context,
    )
    SentMail.objects.create(subscriber=user.subscriber, subject="Bienvenida Papel (PAPYDIM)")


"""
# not used, use if we want to delay a notification
# from background_task import background
# from django.contrib.auth.models import User
@background(schedule=1800)
def notify_user(user_id):
    # lookup user by id and send them a notification
    user = User.objects.get(pk=user_id)
    send_notification(
        user, 'notifications/signup.html', u'¡Te damos la bienvenida!')
"""
