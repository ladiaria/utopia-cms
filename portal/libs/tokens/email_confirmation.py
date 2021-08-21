# -*- coding: utf-8 -*-
from os.path import basename
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.utils.http import int_to_base36, base36_to_int
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.template import RequestContext, loader

from libs.utils import smtp_connect


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """
    Strategy object used to generate and check tokens for the email confirmation mechanism.
    """

    def __init__(self, *args, **kwargs):
        if 'edition_download' in kwargs:
            self.edition_download = kwargs.get('edition_download')
            del(kwargs['edition_download'])
        else:
            self.edition_download = None
        super(EmailConfirmationTokenGenerator, self).__init__(*args, **kwargs)

    def make_token(self, user):
        """
        Returns a token that can be used once to do a password reset
        for the given user.
        """
        return self._make_token_with_timestamp(user, self._num_days(self._today()))

    def check_token(self, user, token, timeout_days=None):
        """
        Check that a password reset token is correct for a given user.
        """
        # Parse the token
        try:
            ts_b36, hash = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if self._make_token_with_timestamp(user, ts) != token:
            return False

        # Check the timestamp is within limit
        if not timeout_days:
            timeout_days = getattr(settings, 'EMAIL_CONFIRMATION_TIMEOUT_DAYS', None)
        if timeout_days and (self._num_days(self._today()) - ts) > timeout_days:
            return False

        return True

    def _make_token_with_timestamp(self, user, timestamp):
        # from django.utils.hashcompat import sha_constructor
        from hashlib import sha1

        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)
        hash = (
            unicode(settings.SECRET_KEY) + unicode(user.id) + unicode(user.email) + unicode(bool(user.is_active)) +
            unicode(timestamp))
        if self.edition_download:
            hash += str(user.get_profile().get_downloads())
        else:
            hash += unicode(user.password)
        return "%s-%s" % (ts_b36, sha1(hash).hexdigest()[::2])


default_token_generator = EmailConfirmationTokenGenerator()
download_token_generator = EmailConfirmationTokenGenerator(edition_download=True)


def send_confirmation_link(*args, **kwargs):
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
    )
    smtp = smtp_connect()
    try:
        smtp.sendmail(settings.NOTIFICATIONS_FROM_MX, [user.email], message.as_string())
        if settings.DEBUG:
            print('DEBUG: an email was sent from send_confirmation_link function')
        smtp.quit()
    except Exception:
        # fail silently
        pass


def send_validation_email(subject, user, msg_template, url_generator, extra_context={}):
    extra_context.update(
        {
            'SITE_URL': settings.SITE_URL,
            'URL_SCHEME': settings.URL_SCHEME,
            'site': Site.objects.get_current(),
            'logo_url': settings.HOMEV3_SECONDARY_LOGO,
        },
    )
    send_confirmation_link(
        extra_context.get('request'),
        subject=subject,
        message_template=msg_template,
        user=user,
        url_generator=url_generator,
        extra_context=extra_context,
    )


def get_signup_validation_url(user):
    return reverse(
        'account-signup-hash', kwargs={'user_id': str(user.id), 'hash': default_token_generator.make_token(user)})
