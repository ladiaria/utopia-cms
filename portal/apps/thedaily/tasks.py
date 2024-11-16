# -*- coding: utf-8 -*-
from email.utils import make_msgid
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from libs.utils import smtp_connect
from thedaily.models import SentMail


welcome_email_sub = 'Tu suscripción %s está activa'


def send_notification_message(subject, message, mailto):
    if (
        not settings.LOCAL_EMAIL_BACKEND_TEST
        and settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'
    ):
        # send using smtp to receive bounces in another mailbox
        s = smtp_connect()
        s.sendmail(settings.NOTIFICATIONS_FROM_MX, [mailto], message.as_string())
        s.quit()
    else:
        # normal django send
        send_mail(subject, message.as_string(), settings.NOTIFICATIONS_FROM_MX, [mailto])


def send_notification(user, email_template, email_subject, extra_context={}):
    extra_context.update(
        {
            'SITE_URL_SD': settings.SITE_URL_SD,
            'site': Site.objects.get_current(),
            'logo_url': settings.HOMEV3_SECONDARY_LOGO,
        }
    )
    msg = Message(
        html=render_to_string(email_template, extra_context),
        mail_to=(user.get_full_name(), user.email),
        subject=email_subject,
        mail_from=(settings.NOTIFICATIONS_FROM_NAME, settings.NOTIFICATIONS_FROM_ADDR1),
        headers={'Message-Id': make_msgid("u." + str(user.id)), "Return-Path": settings.NOTIFICATIONS_FROM_MX}
    )
    send_notification_message(email_subject, msg, user.email)


def notify_subscription(user, subscription_type, seller_fullname=None):
    site = Site.objects.get_current()
    subj_inner = getattr(settings, "THEDAILY_WELCOME_EMAIL_SUBJECT_INNER", {}).get(subscription_type, f"a {site.name}")
    send_notification(
        user,
        settings.THEDAILY_WELCOME_EMAIL_TEMPLATES.get(subscription_type, 'notifications/new_subscription.html'),
        welcome_email_sub % subj_inner,
        {'seller_fullname': seller_fullname} if seller_fullname else {},
    )
    SentMail.objects.create(subscriber=user.subscriber, subject=f"Bienvenida {subj_inner}")


"""
# Example to delay a notification. TODO: rewrite to be used as a celery task
# from background_task import background
# from django.contrib.auth.models import User
@background(schedule=1800)
def notify_user(user_id):
    # lookup user by id and send them a notification
    user = User.objects.get(pk=user_id)
    send_notification(
        user,
        'notifications/signup.html',
        '¡Te damos la bienvenida!',
        {"signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS},
    )
"""
