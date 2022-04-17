# -*- coding: utf-8 -*-
# utopia-cms, 2018-2021, Aníbal Pacheco
import sys
from os.path import basename, join
import logging
import smtplib
import time
import json
from unicodecsv import reader, writer
from MySQLdb import ProgrammingError
from datetime import date, datetime, timedelta
from socket import error
from hashids import Hashids
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.db import close_old_connections, connection, IntegrityError, OperationalError
from django.core.management.base import BaseCommand, CommandError
from django.template import Engine, Context
from django.contrib.sites.models import Site
from django.utils import translation

from apps import blacklisted
from core.models import Category, CategoryNewsletter, Section, Article, get_latest_edition
from core.templatetags.core_tags import remove_markup
from thedaily.models import Subscriber
from thedaily.utils import subscribers_nl_iter, subscribers_nl_iter_filter
from dashboard.models import NewsletterDelivery
from libs.utils import smtp_connect


# CFG
today, EMAIL_ATTACH, ATTACHMENTS = date.today(), True, []

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


def build_and_send(
    category,
    no_deliver,
    offline,
    export_subscribers,
    export_context,
    site_id,
    starting_from_s,
    starting_from_ns,
    partitions,
    mod,
    subscriber_ids,
):

    site = Site.objects.get(id=site_id) if site_id else Site.objects.get_current()
    category_slug, export_only = category if offline else category.slug, export_subscribers or export_context
    context = {'category': category, 'newsletter_campaign': category_slug}
    export_ctx = {'newsletter_campaign': category_slug}

    try:

        offline_ctx_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_ctx.json' % category_slug)
        offline_csv_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_subscribers.csv' % category_slug)
        if offline:
            if starting_from_s or starting_from_ns:
                log.error('--starting-from* options for offline usage not yet implemented')
                return
            context = json.loads(open(offline_ctx_file).read())
        elif not export_subscribers or export_context:
            category_nl = CategoryNewsletter.objects.get(category=category, valid_until__gt=datetime.now())
            cover_article, featured_article = category_nl.cover(), category_nl.featured_article()
            if export_context:
                export_ctx.update(
                    {
                        'articles': [
                            (
                                a.nl_serialize(), {'name': section.name, 'slug': section.slug}
                            ) for a, section in [
                                (a, a.publication_section()) for a in category_nl.non_cover_articles()
                            ]
                        ],
                        # TODO: featured_* entries
                    }
                )
            else:
                context.update(
                    {
                        'cover_article_section': cover_article.publication_section().name if cover_article else None,
                        'articles': [(a, a.publication_section()) for a in category_nl.non_cover_articles()],
                        'featured_article_section':
                            featured_article.publication_section() if featured_article else None,
                        'featured_articles': [
                            (a, a.publication_section()) for a in category_nl.non_cover_featured_articles()
                        ],
                    }
                )

    except CategoryNewsletter.DoesNotExist:

        if not (offline or export_subscribers) or export_context:
            cover_article = category.home.cover()
            cover_article_section = cover_article.publication_section() if cover_article else None
            top_articles = [(a, a.publication_section()) for a in category.home.non_cover_articles()]

            listonly_section = getattr(settings, 'CORE_CATEGORY_NEWSLETTER_LISTONLY_SECTIONS', {}).get(category_slug)
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
                featured_section, days_ago = settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS[category_slug]
                featured_article = category.section_set.get(slug=featured_section).latest_article()[0]
                assert (featured_article.date_published >= datetime.now() - timedelta(days_ago))
            except (KeyError, Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError, AssertionError):
                featured_article = None

            if export_context:
                export_ctx['articles'] = [
                    (t[0].nl_serialize(), {'name': t[1].name, 'slug': t[1].slug}) for t in top_articles
                ]
            else:
                context.update(
                    {
                        'opinion_article': opinion_article,
                        'cover_article_section': cover_article_section,
                        'articles': top_articles,
                    }
                )

    # any custom attached files
    # TODO: make this a feature in the admin using adzone also make it path-setting instead of absolute
    # f_ads = ['/srv/ldsocial/portal/media/document.pdf']
    f_ads = []

    if not offline:
        receivers = Subscriber.objects.filter(user__is_active=True).exclude(user__email='')
        if subscriber_ids:
            receivers = receivers.filter(id__in=subscriber_ids)
        else:
            receivers = receivers.filter(category_newsletters__slug=category_slug).exclude(user__email__in=blacklisted)
            # if both "starting_from" we can filter now with the minimum
            if starting_from_s and starting_from_ns:
                receivers = receivers.filter(user__email__gt=min(starting_from_s, starting_from_ns))
            if partitions is not None and mod is not None:
                receivers = receivers.extra(where=['MOD(%s.id,%d)=%d' % (Subscriber._meta.db_table, partitions, mod)])

    if offline:
        custom_subject = context['custom_subject']
        email_subject = context['email_subject']
        email_from = context['email_from']
        site_url = context['site_url']
        list_id = context['list_id']
        ga_property_id = context['ga_property_id']
        r = reader(open(offline_csv_file))
        if subscriber_ids:
            subscribers_iter = subscribers_nl_iter_filter(r, lambda row: int(row[0]) in subscriber_ids)
        elif partitions is not None and mod is not None:
            subscribers_iter = subscribers_nl_iter_filter(r, lambda row: int(row[0]) % partitions == mod)
        else:
            subscribers_iter = r
    elif not export_subscribers or export_context:
        site_url = '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN)
        list_id = '%s <%s.%s>' % (category_slug, __name__, settings.SITE_DOMAIN)
        ga_property_id = getattr(settings, 'GA_PROPERTY_ID', None)
        custom_subject = category.newsletter_automatic_subject is False and category.newsletter_subject
        email_subject = custom_subject or (
            getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_PREFIX', {}).get(category_slug, u'')
            + remove_markup(cover_article.headline)
        )

        email_from = (
            site.name if category_slug in getattr(
                settings, 'CORE_CATEGORY_NL_FROM_NAME_SITEONLY', ()
            ) else (u'%s %s' % (site.name, category.name)),
            settings.NOTIFICATIONS_FROM_ADDR1,
        )

    translation.activate(settings.LANGUAGE_CODE)

    if not export_subscribers or export_context:
        common_ctx = {'site_url': site_url, 'ga_property_id': ga_property_id, 'custom_subject': custom_subject}
    if export_only:
        if export_context:
            export_ctx.update(common_ctx)
            export_ctx.update(
                {
                    'email_subject': email_subject,
                    'email_from': email_from,
                    'list_id': list_id,
                    'cover_article': cover_article.nl_serialize(True),
                }
            )
            # TODO: 'featured_article' entry
            open(offline_ctx_file, 'w').write(json.dumps(export_ctx))
        if export_subscribers:
            export_subscribers_writer = writer(open(offline_csv_file, 'w'))
        else:
            return
    elif not offline:
        context.update(common_ctx)
        context.update({'cover_article': cover_article, 'featured_article': featured_article})

    if not offline:
        subscribers_iter = subscribers_nl_iter(receivers, starting_from_s, starting_from_ns)

    # Connect to the SMTP server and send all emails
    try:
        smtp = None if no_deliver or export_only else smtp_connect()
    except error:
        log.error("MTA down, '%s %s' was used for partitions and mod" % (partitions, mod))
        return

    subscriber_sent, user_sent, subscriber_refused, user_refused = 0, 0, 0, 0
    retry_last_delivery, s_id, is_subscriber = False, None, None
    email_template = Engine.get_default().get_template(
        '%s/newsletter/%s.html' % (settings.CORE_CATEGORIES_TEMPLATE_DIR, category_slug)
    )

    while True:

        try:
            if not retry_last_delivery:
                if offline:
                    s_id, s_name, s_user_email, hashed_id, is_subscriber, is_subscriber_any, is_subscriber_default = (
                        subscribers_iter.next()
                    )
                    is_subscriber = eval(is_subscriber)
                    is_subscriber_any = eval(is_subscriber_any)
                    is_subscriber_default = eval(is_subscriber_default)
                else:
                    s, is_subscriber = subscribers_iter.next()
                    s_id, s_name, s_user_email = s.id, s.name, s.user.email
                    hashed_id = hashids.encode(int(s_id))
                    is_subscriber_any = s.is_subscriber_any()
                    is_subscriber_default = s.is_subscriber(settings.DEFAULT_PUB)

            if export_subscribers:
                export_subscribers_writer.writerow(
                    [s_id, s_name, s_user_email, hashed_id, is_subscriber, is_subscriber_any, is_subscriber_default]
                )
            elif not export_context:
                headers = {'List-ID': list_id}
                unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
                    '&utm_campaign=%s&utm_content=unsubscribe' % (site_url, category_slug, hashed_id, category_slug)
                headers['List-Unsubscribe'] = headers['List-Unsubscribe-Post'] = '<%s>' % unsubscribe_url
                context.update(
                    {
                        'hashed_id': hashed_id,
                        'unsubscribe_url': unsubscribe_url,
                        'subscriber_id': s_id,
                        'is_subscriber': is_subscriber,
                        'is_subscriber_any': is_subscriber_any,
                        'is_subscriber_default': is_subscriber_default,
                    }
                )

                msg = Message(
                    html=email_template.render(Context(context)),
                    mail_to=(s_name, s_user_email),
                    subject=email_subject,
                    mail_from=email_from,
                    headers=headers,
                )

                # attach ads if any
                for f_ad in f_ads:
                    f_ad_basename = basename(f_ad)
                    msg.attach(filename=f_ad_basename, data=open(f_ad, "rb"))

                # send using smtp to receive bounces in another mailbox
                try:
                    if not no_deliver:
                        smtp.sendmail(settings.NOTIFICATIONS_FROM_MX, [s_user_email], msg.as_string())
                    log.info(
                        "Email %s to %ssubscriber %s\t%s" % (
                            'simulated' if no_deliver else 'sent', '' if is_subscriber else 'non-', s_id, s_user_email
                        )
                    )
                    if is_subscriber:
                        subscriber_sent += 1
                    else:
                        user_sent += 1
                except smtplib.SMTPRecipientsRefused:
                    log.warning(
                        "Email refused for %ssubscriber %s\t%s" % ('' if is_subscriber else 'non-', s_id, s_user_email)
                    )
                    if is_subscriber:
                        subscriber_refused += 1
                    else:
                        user_refused += 1
                except smtplib.SMTPServerDisconnected:
                    # Retries are made only once per iteration to avoid infinite loop if MTA got down at all
                    retry_last_delivery = not retry_last_delivery
                    log_message = "MTA down, email to %s not sent. Reconnecting " % s_user_email
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
                    'DB connection error, (%s, %s, %s, %s) was the last delivery attempt' % (
                        s_user_email if s_id else None, is_subscriber, partitions, mod
                    )
                )
            break

    if not export_only:
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
                    """ % (today, category_slug, user_sent, subscriber_sent, user_refused, subscriber_refused)
                )
                cursor.execute('COMMIT')
            except IntegrityError:
                nl_delivery = NewsletterDelivery.objects.get(delivery_date=today, newsletter_name=category_slug)
                nl_delivery.user_sent = (nl_delivery.user_sent or 0) + user_sent
                nl_delivery.subscriber_sent = (nl_delivery.subscriber_sent or 0) + subscriber_sent
                nl_delivery.user_refused = (nl_delivery.user_refused or 0) + user_refused
                nl_delivery.subscriber_refused = (nl_delivery.subscriber_refused or 0) + subscriber_refused
                nl_delivery.save()
            except Exception as e:
                log.error(u'Delivery stats not updated: %s' % e)

        log.info(
            u'%s stats: user_sent: %d, subscriber_sent: %s, user_refused: %d, subscriber_refused: %d' % (
                'Simulation' if no_deliver else 'Delivery',
                user_sent,
                subscriber_sent,
                user_refused,
                subscriber_refused,
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
            '--offline',
            action='store_true',
            default=False,
            dest='offline',
            help='Do not use the database to fetch email data, get it from datasets previously generated',
        )
        parser.add_argument(
            '--export-subscribers',
            action='store_true',
            default=False,
            dest='export_subscribers',
            help='Not send and export the subscribers dataset for offline usage later with the option --offline',
        )
        parser.add_argument(
            '--export-context',
            action='store_true',
            default=False,
            dest='export_context',
            help='Not send and export the context dataset for offline usage later with the option --offline',
        )
        parser.add_argument(
            '--site-id',
            action='store',
            type=int,
            dest='site_id',
            help='Use another site instead of the current site to build the URLs inside the message',
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
            '--partitions',
            action='store',
            type=int,
            dest='partitions',
            help=u'Used with --mod, divide receipts in this quantity of partitions e.g.: --partitions=5',
        )
        parser.add_argument(
            '--mod',
            action='store',
            type=int,
            dest='mod',
            help=u'When --partitions is set, only take receipts whose id MOD partitions == this value e.g.: --mod=0',
        )

    def handle(self, *args, **options):
        partitions, mod, offline = options.get('partitions'), options.get('mod'), options.get('offline')
        export_subscribers, export_context = options.get('export_subscribers'), options.get('export_context')
        export_only = export_subscribers or export_context
        if offline and export_only:
            raise CommandError('--export-* options can not be used with --offline')
        if partitions is None and mod is not None or mod is None and partitions is not None:
            raise CommandError(u'--partitions must be used with --mod')
        category_slug = options.get('category_slug')[0]
        try:
            no_deliver = options.get('no_deliver')
            category = category_slug if offline else Category.objects.get(slug=category_slug)
        except Category.DoesNotExist:
            raise CommandError(u'No category matching the slug given found')
        if not export_only:
            h = logging.FileHandler(
                filename=settings.SENDNEWSLETTER_LOGFILE % (category_slug, today.strftime('%Y%m%d'))
            )
            h.setFormatter(log_formatter)
            log.addHandler(h)
            start_time = time.time()
        build_and_send(
            category,
            no_deliver,
            offline,
            export_subscribers,
            export_context,
            options.get('site_id'),
            options.get('starting_from_s'),
            options.get('starting_from_ns'),
            partitions,
            mod,
            options.get('subscriber_ids'),
        )
        if not export_only:
            log.info(
                "%s completed in %.0f seconds" % ('Simulation' if no_deliver else 'Delivery', time.time() - start_time)
            )
