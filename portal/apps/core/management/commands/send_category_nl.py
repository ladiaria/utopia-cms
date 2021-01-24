# -*- coding: utf-8 -*-
# utopia-cms, 2018-2021, Aníbal Pacheco

import os
import logging
import csv
import smtplib
import time
from datetime import date, datetime, timedelta
from threading import Thread
from hashids import Hashids
from optparse import make_option
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.db import connection, IntegrityError
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from core.models import Category, Section, Article, get_latest_edition
from core.templatetags.core_tags import remove_markup
from home.models import Home
from thedaily.models import Subscriber
from dashboard.models import NewsletterDelivery
from libs.utils import smtp_connect
from libs.thread_iter import threadsafe_generator

# CFG
today = date.today()
EMAIL_FROM_ADDR = 'suscriptores@ladiaria.com.uy'
EMAIL_ATTACH, ATTACHMENTS = True, []

# log
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


def build_and_send(category, nthreads, no_deliver, starting_from_s, starting_from_ns, ids_ending_with, subscriber_ids):

    category_home = Home.objects.get(category=category)
    cat_modules = category_home.modules.all()

    cover_article = category_home.cover

    cover_article_section = cover_article.publication_section()
    top_articles = [(a, a.publication_section(), 0) for a in (cat_modules[0].articles_as_list if cat_modules else [])]

    opinion_article = None
    nl_featured = Article.objects.filter(id=settings.NEWSLETTER_FEATURED_ARTICLE) if \
        getattr(settings, 'NEWSLETTER_FEATURED_ARTICLE', False) else \
        get_latest_edition().newsletter_featured_articles()
    if nl_featured:
        opinion_article = nl_featured[0]

    # datos_article (a featured section in the category)
    try:
        datos_article = category.section_set.get(slug='datos').latest_article()[0]
        assert (datos_article.date_published >= datetime.now() - timedelta(1))
    except (Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError, AssertionError):
        datos_article = None

    # any custom attached files
    # TODO: make this a feature in the admin using adzone also make it path-setting instead of absolute
    # f_ads = ['/srv/ldsocial/portal/media/document.pdf']
    f_ads = []

    filter_args = {'user__is_active': True}
    if subscriber_ids:
        filter_args['id__in'] = subscriber_ids
    else:
        filter_args['category_newsletters__slug'] = category.slug
        if ids_ending_with:
            filter_args['id__iregex'] = r'^\d*[%s]$' % ids_ending_with

    blacklisted = set([row[0] for row in csv.reader(open(settings.CORE_NEWSLETTER_BLACKLIST))])

    # iterate over receivers and yield the subscribers first, saving the
    # not subscribers ids in a temporal list an then yield them also
    @threadsafe_generator
    def subscribers():
        receivers2 = []
        for s in Subscriber.objects.filter(**filter_args).distinct().order_by('user__email').iterator():
            if s.user and s.user.email and s.user.email not in blacklisted:
                if s.is_subscriber():
                    if not starting_from_s or (starting_from_s and s.user.email > starting_from_s):
                        yield s, True
                else:
                    if not starting_from_ns or (starting_from_ns and s.user.email > starting_from_ns):
                        receivers2.append(s.id)
        for sus_id in receivers2:
            yield Subscriber.objects.get(id=sus_id), False

    # create global counters
    counters = []

    # define the function to be executed by each thread
    def send(func):
        # Connect to the SMTP server and send all emails
        smtp = smtp_connect()

        subscriber_sent, user_sent, subscriber_refused, user_refused = 0, 0, 0, 0
        site_url = '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN)
        list_id = '%s <%s.%s>' % (category.slug, __name__, settings.SITE_DOMAIN)

        # iterate and send
        while True:

            try:
                s, is_subscriber = func()
                headers, hashed_id = {'List-ID': list_id}, hashids.encode(int(s.id))
                unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
                    '&utm_campaign=%s&utm_content=unsubscribe' % (site_url, category.slug, hashed_id, category.slug)
                headers['List-Unsubscribe'] = headers['List-Unsubscribe-Post'] = '<%s>' % unsubscribe_url

                msg = Message(
                    html=render_to_string(
                        '%s/newsletter/%s.html' % (settings.CORE_CATEGORIES_TEMPLATE_DIR, category.slug),
                        {
                            'cover_article': cover_article,
                            'category': category,
                            'opinion_article': opinion_article,
                            'datos_article': datos_article,
                            'site_url': site_url,
                            'articles': top_articles,
                            'unsubscribe_url': unsubscribe_url,
                            'ga_property_id': getattr(settings, 'GA_PROPERTY_ID', None),
                            'subscriber_id': s.id,
                            'is_subscriber': is_subscriber,
                            'cover_article_section': cover_article_section,
                        }
                    ),
                    mail_to=(s.name, s.user.email), subject=remove_markup(cover_article.headline),
                    mail_from=(u'la diaria ' + category.name, EMAIL_FROM_ADDR), headers=headers,
                )

                # attach ads if any
                for f_ad in f_ads:
                    f_ad_basename = os.path.basename(f_ad)
                    msg.attach(filename=f_ad_basename, data=open(f_ad, "rb"))

                # send using smtp to receive bounces in another mailbox
                try:
                    if not no_deliver:
                        smtp.sendmail(settings.NOTIFICATIONS_FROM_MX, [s.user.email], msg.as_string())
                    log.info("%s Email %s to %ssubscriber %s\t%s" % (
                        today, 'simulated' if no_deliver else 'sent', '' if is_subscriber else 'non-',
                        s.id, s.user.email))
                    if is_subscriber:
                        subscriber_sent += 1
                    else:
                        user_sent += 1
                except smtplib.SMTPRecipientsRefused:
                    log.warning("%s Email refused for %ssubscriber %s\t%s" % (
                        today, '' if is_subscriber else 'non-', s.id, s.user.email))
                    if is_subscriber:
                        subscriber_refused += 1
                    else:
                        user_refused += 1
                except smtplib.SMTPServerDisconnected:
                    log.error("MTA down, not sending - %s" % s.user.email)
                    log.info("Trying to reconnect for the next delivery...")
                    smtp = smtp_connect()

            except StopIteration:
                # append data processed to global results and quit.
                # this can be done because list.append is threadsafe.
                counters.append((subscriber_sent, user_sent, subscriber_refused, user_refused))
                break

        try:
            smtp.quit()
        except smtplib.SMTPServerDisconnected:
            pass

    # create threads
    subscribers_iter = subscribers()
    threads = [Thread(target=send, args=(subscribers_iter.next, )) for i in range(nthreads)]

    # start threads
    for t in threads:
        t.start()

    # wait for threads to finish
    for t in threads:
        t.join()

    # sum total counters
    subscriber_sent, user_sent, subscriber_refused, user_refused = 0, 0, 0, 0
    for counter0, counter1, counter2, counter3 in counters:
        subscriber_sent += counter0
        user_sent += counter1
        subscriber_refused += counter2
        user_refused += counter3

    # update log stats counters only if subscriber_ids not given
    if not subscriber_ids:
        try:
            # A transaction is needed because autocommit in django is broken in concurrent management processes
            cursor = connection.cursor()
            cursor.execute('BEGIN')
            cursor.execute("""INSERT INTO dashboard_newsletterdelivery(
                delivery_date,newsletter_name,user_sent,subscriber_sent,user_refused,subscriber_refused)
                VALUES('%s','%s',%d,%d,%d,%d)""" % (
                today, category.slug, user_sent, subscriber_sent, user_refused, subscriber_refused))
            cursor.execute('COMMIT')
        except IntegrityError:
            nl_delivery = NewsletterDelivery.objects.get(delivery_date=today, newsletter_name=category.slug)
            nl_delivery.user_sent = (nl_delivery.user_sent or 0) + user_sent
            nl_delivery.subscriber_sent = (nl_delivery.subscriber_sent or 0) + subscriber_sent
            nl_delivery.user_refused = (nl_delivery.user_refused or 0) + user_refused
            nl_delivery.subscriber_refused = (nl_delivery.subscriber_refused or 0) + subscriber_refused
            nl_delivery.save()
        except Exception as e:
            log.error(u'%s ERROR: Delivery stats not updated: %s' % (today, e))

    log.info((u'%s %s stats: user_sent: %d, subscriber_sent: %s, user_refused: %d, subscriber_refused: %d') % (
        today, 'Simulation' if no_deliver else 'Delivery', user_sent, subscriber_sent, user_refused,
        subscriber_refused))


class Command(BaseCommand):
    args = '<category_slug [subscriber_id1 id2 ...]>'
    help = 'Sends the last category newsletter by email to all subscribers of the category given or those given by id.'

    option_list = BaseCommand.option_list + (
        make_option(
            '--nthreads',
            action='store',
            type='int',
            dest='nthreads',
            default=2,
            help='Number of threads to use for delivery, default 2.',
        ),
        make_option(
            '--no-deliver',
            action='store_true',
            default=False,
            dest='no_deliver',
            help=u'Do not send the emails, only log',
        ),
        make_option(
            '--starting-from-s',
            action='store',
            type='string',
            dest='starting_from_s',
            help=u'Send only subscriptors emails alphabetically greather',
        ),
        make_option(
            '--starting-from-ns',
            action='store',
            type='string',
            dest='starting_from_ns',
            help=u'Send only no subscriptors emails alphabetically greather',
        ),
        make_option(
            '--ids-ending-with',
            action='store',
            type='string',
            dest='ids_ending_with',
            help=u'Send only to subscriptors with id ending in this numbers e.g.: --ids-ending-with=0123',
        ),
    )

    def handle(self, *args, **options):
        category_slug = args[0]
        log.addHandler(logging.FileHandler(filename=settings.SENDNEWSLETTER_LOGFILE % category_slug))
        category = Category.objects.get(slug=category_slug)
        no_deliver = options.get('no_deliver')
        start_time, nthreads = time.time(), options.get('nthreads')
        build_and_send(
            category,
            nthreads,
            no_deliver,
            options.get('starting_from_s'),
            options.get('starting_from_ns'),
            options.get('ids_ending_with'),
            args[1:],
        )
        log.info("%s %s completed in %.0f seconds using %d threads" % (
            today, 'Simulation' if no_deliver else 'Delivery', time.time() - start_time, nthreads))
