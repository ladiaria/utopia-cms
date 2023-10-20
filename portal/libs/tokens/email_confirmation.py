# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

from builtins import str

from email.utils import make_msgid
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail
from django.contrib.sites.models import Site
from django.contrib.auth.tokens import default_token_generator
from django.template import loader

from libs.utils import smtp_connect
from utils.error_log import error_log


def send_confirmation_link(*args, **kwargs):
    result = False
    request = args[0]
    subject = kwargs['subject']
    message_template = kwargs['message_template']
    user = kwargs['user']
    if 'edition' in kwargs:
        generator_params = {'user': kwargs['user'], 'edition': kwargs['edition']}
    else:
        generator_params = {'user': kwargs['user']}
    url_generator = kwargs['url_generator']
    extra_context = kwargs['extra_context']
    from_mail = getattr(settings, 'DEFAULT_FROM_EMAIL')
    subject = '%s %s' % (getattr(settings, 'EMAIL_SUBJECT_PREFIX', ''), subject)
    context = {'validation_url': url_generator(**generator_params)}
    if extra_context:
        context.update(extra_context)
    message = Message(
        html=loader.render_to_string(message_template, context, request),
        mail_to=(user.first_name, user.email),
        mail_from=from_mail,
        subject=subject,
        headers={'Message-Id': make_msgid("u." + str(user.id)), "Return-Path": settings.NOTIFICATIONS_FROM_MX}
    )
    if (
        not getattr(settings, 'LOCAL_EMAIL_BACKEND_TEST', False)
        and settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'
    ):
        smtp = smtp_connect()
        try:
            smtp.sendmail(settings.NOTIFICATIONS_FROM_MX, [user.email], message.as_string())
            if settings.DEBUG:
                print('DEBUG: an email was sent from send_confirmation_link function')
            smtp.quit()
            result = True  # success confirmation
        except Exception as e:
            error_log('Error sending confirmation email'.format(str(e)))

    else:
        try:
            result = send_mail(subject, message.as_string(), settings.NOTIFICATIONS_FROM_MX, [user.email]) > 0
        except Exception as e:
            error_log('Error sending confirmation email'.format(str(e)))

    return result


def send_validation_email(subject, user, msg_template, url_generator, extra_context={}):
    extra_context.update(
        {
            'SITE_URL': settings.SITE_URL,
            'URL_SCHEME': settings.URL_SCHEME,
            'site': Site.objects.get_current(),
            'logo_url': settings.HOMEV3_SECONDARY_LOGO,
        },
    )
    return send_confirmation_link(
        extra_context.get('request'),
        subject=subject,
        message_template=msg_template,
        user=user,
        url_generator=url_generator,
        extra_context=extra_context,
    )


def get_signup_validation_url(user):
    return reverse(
        'account-signup-hash', kwargs={'user_id': str(user.id), 'hash': default_token_generator.make_token(user)}
    )
