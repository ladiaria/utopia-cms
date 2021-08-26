# -*- coding: utf-8 -*-
# utopia-cms, 2018-2021, Aníbal Pacheco
import sys
import os
import logging
import smtplib
import time
from MySQLdb import ProgrammingError
from datetime import date, datetime, timedelta
from socket import error
from hashids import Hashids
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.db import close_old_connections, connection, IntegrityError, OperationalError
from django.core.management.base import BaseCommand
from django.template import Engine, Context
from django.contrib.sites.models import Site
from django.utils import translation

from apps import blacklisted
from core.models import Category, Section, Article, get_latest_edition
from core.templatetags.core_tags import remove_markup
from thedaily.models import Subscriber
from thedaily.utils import subscribers_nl_iter
from dashboard.models import NewsletterDelivery
from libs.utils import smtp_connect


# CFG
today = date.today()
site = Site.objects.get_current()
EMAIL_ATTACH, ATTACHMENTS = True, []

# log
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', '%H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
# print also errors to stderr to receive cron alert
err_handler = logging.StreamHandler(sys.stderr)
err_handler.setLevel(logging.ERROR)
err_handler.setFormatter(log_formatter)
log.addHandler(err_handler)

# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


def build_and_send(category, no_deliver, starting_from_s, starting_from_ns, ids_ending_with, subscriber_ids):

    cover_article = category.home.cover()
    cover_article_section = cover_article.publication_section() if cover_article else None
    top_articles = [(a, a.publication_section()) for a in category.home.non_cover_articles()]

    listonly_section = getattr(settings, 'CORE_CATEGORY_NEWSLETTER_LISTONLY_SECTIONS', {}).get(category.slug)
    if listonly_section:
        top_articles = [t for t in top_articles if t[1].slug == listonly_section]
        if cover_article_section.slug != listonly_section:
            cover_article = top_articles.pop(0)[0] if top_articles else None
            cover_article_section = cover_article.publication_section() if cover_article else None

    opinion_article = None
    nl_featured = Article.objects.filter(
        id=settings.NEWSLETTER_FEATURED_ARTICLE
    ) if getattr(
        settings, 'NEWSLETTER_FEATURED_ARTICLE', False
    ) else get_latest_edition().newsletter_featured_articles()
    if nl_featured:
        opinion_article = nl_featured[0]

    # featured_article (a featured section in the category)
    try:
        featured_section, days_ago = settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS[category.slug]
        featured_article = category.section_set.get(slug=featured_section).latest_article()[0]
        assert (featured_article.date_published >= datetime.now() - timedelta(days_ago))
    except (KeyError, Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError, AssertionError):
        featured_article = None

    # any custom attached files
    # TODO: make this a feature in the admin using adzone also make it path-setting instead of absolute
    # f_ads = ['/srv/ldsocial/portal/media/document.pdf']
    f_ads = []

    receivers = Subscriber.objects.filter(user__is_active=True).exclude(user__email='')
    if subscriber_ids:
        receivers = receivers.filter(id__in=subscriber_ids)
    else:
        receivers = receivers.filter(category_newsletters__slug=category.slug).exclude(user__email__in=blacklisted)
        # if both "starting_from" we can filter now with the minimum
        if starting_from_s and starting_from_ns:
            receivers = receivers.filter(user__email__gt=min(starting_from_s, starting_from_ns))
        if ids_ending_with:
            receivers = receivers.filter(id__iregex=r'^\d*[%s]$' % ids_ending_with)

    # Connect to the SMTP server and send all emails
    try:
        smtp = None if no_deliver else smtp_connect()
    except error:
        log.error("MTA down, '%s' was used for ids_ending_with" % ids_ending_with)
        return

    subscriber_sent, user_sent, subscriber_refused, user_refused = 0, 0, 0, 0
    site_url = '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN)
    list_id = '%s <%s.%s>' % (category.slug, __name__, settings.SITE_DOMAIN)

    # fixed email data
    email_template = Engine.get_default().get_template(
        '%s/newsletter/%s.html' % (settings.CORE_CATEGORIES_TEMPLATE_DIR, category.slug)
    )
    ga_property_id = getattr(settings, 'GA_PROPERTY_ID', None)
    email_subject = (
        getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_PREFIX', {}).get(category.slug, u'')
        + remove_markup(cover_article.headline)
    )
    email_from = (
        site.name if category.slug in getattr(
            settings, 'CORE_CATEGORY_NL_FROM_NAME_SITEONLY', ()
        ) else (u'%s %s' % (site.name, category.name)),
        settings.NOTIFICATIONS_FROM_ADDR1,
    )
    translation.activate(settings.LANGUAGE_CODE)

    # iterate and send
    retry_last_delivery, s, is_subscriber = False, None, None
    subscribers_iter = subscribers_nl_iter(receivers, starting_from_s, starting_from_ns)
    while True:

        try:
            if not retry_last_delivery:
                s, is_subscriber = subscribers_iter.next()
            headers, hashed_id = {'List-ID': list_id}, hashids.encode(int(s.id))
            unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
                '&utm_campaign=%s&utm_content=unsubscribe' % (site_url, category.slug, hashed_id, category.slug)
            headers['List-Unsubscribe'] = headers['List-Unsubscribe-Post'] = '<%s>' % unsubscribe_url

            msg = Message(
                html=email_template.render(
                    Context(
                        {
                            'site_url': site_url,
                            'category': category,
                            'featured_article': featured_article,
                            'opinion_article': opinion_article,
                            'cover_article': cover_article,
                            'cover_article_section': cover_article_section,
                            'articles': top_articles,
                            'newsletter_campaign': category.slug,
                            'hashed_id': hashed_id,
                            'unsubscribe_url': unsubscribe_url,
                            'ga_property_id': ga_property_id,
                            'subscriber_id': s.id,
                            'is_subscriber': is_subscriber,
                        }
                    )
                ),
                mail_to=(s.name, s.user.email),
                subject=email_subject,
                mail_from=email_from,
                headers=headers,
            )

            # attach ads if any
            for f_ad in f_ads:
                f_ad_basename = os.path.basename(f_ad)
                msg.attach(filename=f_ad_basename, data=open(f_ad, "rb"))

            # send using smtp to receive bounces in another mailbox
            try:
                if not no_deliver:
                    smtp.sendmail(settings.NOTIFICATIONS_FROM_MX, [s.user.email], msg.as_string())
                log.info(
                    "Email %s to %ssubscriber %s\t%s" % (
                        'simulated' if no_deliver else 'sent', '' if is_subscriber else 'non-', s.id, s.user.email
                    )
                )
                if is_subscriber:
                    subscriber_sent += 1
                else:
                    user_sent += 1
            except smtplib.SMTPRecipientsRefused:
                log.warning(
                    "Email refused for %ssubscriber %s\t%s" % ('' if is_subscriber else 'non-', s.id, s.user.email)
                )
                if is_subscriber:
                    subscriber_refused += 1
                else:
                    user_refused += 1
            except smtplib.SMTPServerDisconnected:
                # Retries are made only once per iteration to avoid infinite loop if MTA got down at all
                retry_last_delivery = not retry_last_delivery
                log_message = "MTA down, email to %s not sent. Reconnecting " % s.user.email
                if retry_last_delivery:
                    log.warning(log_message + "to retry ...")
                else:
                    log.error(log_message + "for the next delivery ...")
                try:
                    smtp = smtp_connect()
                except error:
                    log.warning('MTA reconnect failed')
            else:
                retry_last_delivery = False

        except (ProgrammingError, OperationalError, StopIteration) as exc:
            # the connection to databse can be killed, if that is the case print useful log to continue
            if isinstance(exc, (ProgrammingError, OperationalError)):
                log.error(
                    'DB connection error, (%s, %s, %s) was the last delivery attempt' % (
                        s.user.email if s else None, is_subscriber, ids_ending_with
                    )
                )
            break

    if not no_deliver:
        try:
            smtp.quit()
        except smtplib.SMTPServerDisconnected:
            pass

    # update log stats counters only if subscriber_ids not given
    if not subscriber_ids:
        try:
            # close connections because reach this point can take several minutes
            close_old_connections()
            # A transaction is needed because autocommit in django is broken in concurrent management processes
            cursor = connection.cursor()
            cursor.execute('BEGIN')
            cursor.execute(
                """
                INSERT INTO dashboard_newsletterdelivery(
                    delivery_date,newsletter_name,user_sent,subscriber_sent,user_refused,subscriber_refused
                )
                VALUES('%s','%s',%d,%d,%d,%d)
                """ % (today, category.slug, user_sent, subscriber_sent, user_refused, subscriber_refused)
            )
            cursor.execute('COMMIT')
        except IntegrityError:
            nl_delivery = NewsletterDelivery.objects.get(delivery_date=today, newsletter_name=category.slug)
            nl_delivery.user_sent = (nl_delivery.user_sent or 0) + user_sent
            nl_delivery.subscriber_sent = (nl_delivery.subscriber_sent or 0) + subscriber_sent
            nl_delivery.user_refused = (nl_delivery.user_refused or 0) + user_refused
            nl_delivery.subscriber_refused = (nl_delivery.subscriber_refused or 0) + subscriber_refused
            nl_delivery.save()
        except Exception as e:
            log.error(u'Delivery stats not updated: %s' % e)

    log.info(
        u'%s stats: user_sent: %d, subscriber_sent: %s, user_refused: %d, subscriber_refused: %d' % (
            'Simulation' if no_deliver else 'Delivery', user_sent, subscriber_sent, user_refused, subscriber_refused
        )
    )


class Command(BaseCommand):
    help = 'Sends the last category newsletter by email to all subscribers of the category given or those given by id.'

    def add_arguments(self, parser):
        parser.add_argument('category_slug', nargs=1, type=unicode)
        parser.add_argument('subscriber_ids', nargs='*', type=long)
        parser.add_argument(
            '--no-deliver',
            action='store_true',
            default=False,
            dest='no_deliver',
            help=u'Do not send the emails, only log',
        )
        parser.add_argument(
            '--starting-from-s',
            action='store',
            type=unicode,
            dest='starting_from_s',
            help=u'Send to subscribers only if their email is alphabetically greater than',
        )
        parser.add_argument(
            '--starting-from-ns',
            action='store',
            type=unicode,
            dest='starting_from_ns',
            help=u'Send to non-subscribers only if their email is alphabetically greater than',
        )
        parser.add_argument(
            '--ids-ending-with',
            action='store',
            type=unicode,
            dest='ids_ending_with',
            help=u'Send only if the Subscriber object id ends with one of these numbers e.g.: --ids-ending-with=0123',
        )

    def handle(self, *args, **options):
        category_slug = options.get('category_slug')[0]
        h = logging.FileHandler(filename=settings.SENDNEWSLETTER_LOGFILE % (category_slug, today.strftime('%Y%m%d')))
        h.setFormatter(log_formatter)
        log.addHandler(h)
        category, no_deliver = Category.objects.get(slug=category_slug), options.get('no_deliver')
        start_time = time.time()
        build_and_send(
            category,
            no_deliver,
            options.get('starting_from_s'),
            options.get('starting_from_ns'),
            options.get('ids_ending_with'),
            options.get('subscriber_ids'),
        )
        log.info(
            "%s completed in %.0f seconds" % ('Simulation' if no_deliver else 'Delivery', time.time() - start_time)
        )
