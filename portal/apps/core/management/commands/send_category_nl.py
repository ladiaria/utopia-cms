# -*- coding: utf-8 -*-
# utopia-cms, 2018-2023, Aníbal Pacheco
from __future__ import unicode_literals

from builtins import next

import sys
from os.path import basename, join
import logging
import locale
import smtplib
import time
import json
from datetime import date, datetime, timedelta
from socket import error
from csv import reader, writer
from pydoc import locate
from MySQLdb import ProgrammingError
from hashids import Hashids
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.db import OperationalError
from django.core.management.base import BaseCommand, CommandError
from django.template import Engine, Context
from django.contrib.sites.models import Site
from django.utils import translation

from apps import blocklisted
from core.models import Category, CategoryNewsletter, Section, Article, get_latest_edition
from core.templatetags.ldml import remove_markup
from thedaily.models import Subscriber
from thedaily.utils import subscribers_nl_iter, subscribers_nl_iter_filter
from dashboard.models import NewsletterDelivery
from libs.utils import smtp_connect, smtp_server_choice, smtp_quit


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
    as_news,
    export_subscribers,
    export_context,
    site_id,
    starting_from_s,
    starting_from_ns,
    partitions,
    mod,
    subscriber_ids,
    hide_after_content_block,
):

    site = Site.objects.get(id=site_id) if site_id else Site.objects.get_current()
    category_slug, export_only = category if offline else category.slug, export_subscribers or export_context
    locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)
    export_ctx = {
        'newsletter_campaign': category_slug,
        'nl_date': "{d:%A} {d.day} de {d:%B de %Y}".format(d=today).capitalize(),
        'enable_photo_byline': settings.CORE_ARTICLE_ENABLE_PHOTO_BYLINE,
        'hide_after_content_block': hide_after_content_block,
    }
    context = export_ctx.copy()
    context['category'] = category

    try:

        offline_ctx_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_ctx.json' % category_slug)
        offline_csv_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_subscribers.csv' % category_slug)
        if offline:
            if starting_from_s or starting_from_ns:
                log.error('--starting-from* options for offline usage not yet implemented')
                return
            context = json.loads(open(offline_ctx_file).read())
            # de-serialize dates
            dp_cover = datetime.strptime(context['cover_article']['date_published'], '%Y-%m-%d').date()
            context['cover_article']['date_published'] = dp_cover
            featured_article = context['featured_article']
            if featured_article:
                dp_featured = datetime.strptime(featured_article['date_published'], '%Y-%m-%d').date()
                context['featured_article']['date_published'] = dp_featured
            dp_articles = []
            for a, a_section in context['articles']:
                dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
                a['date_published'] = dp_article
                dp_articles.append((a, a_section))
            context['articles'] = dp_articles
            if 'featured_articles' in context:
                dp_featured_articles = []
                for a, a_section in context['featured_articles']:
                    dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
                    a['date_published'] = dp_article
                    dp_featured_articles.append((a, a_section))
                context['featured_articles'] = dp_featured_articles
        elif not export_subscribers or export_context:
            category_nl = CategoryNewsletter.objects.get(category=category, valid_until__gt=datetime.now())
            cover_article, featured_article = category_nl.cover(), category_nl.featured_article()
            featured_article_section = featured_article.publication_section() if featured_article else None
            if export_context:
                export_ctx.update(
                    {
                        'articles': [
                            (
                                a.nl_serialize(position == 0), {'name': section.name, 'slug': section.slug}
                            ) for position, (a, section) in enumerate(
                                [(a, a.publication_section()) for a in category_nl.non_cover_articles()]
                            )
                        ],
                        'featured_article_section':
                            featured_article_section.name if featured_article_section else None,
                        'featured_articles': [
                            (
                                a.nl_serialize(), {'name': section.name, 'slug': section.slug}
                            ) for a, section in [
                                (a, a.publication_section()) for a in category_nl.non_cover_featured_articles()
                            ]
                        ],
                    }
                )
            else:
                context.update(
                    {
                        'cover_article_section': cover_article.publication_section().name if cover_article else None,
                        'articles': [(a, a.publication_section()) for a in category_nl.non_cover_articles()],
                        'featured_article_section': featured_article_section,
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

            featured_article_id = getattr(settings, 'NEWSLETTER_FEATURED_ARTICLE', False)
            nl_featured = Article.objects.filter(
                id=featured_article_id
            ) if featured_article_id else get_latest_edition().newsletter_featured_articles()
            opinion_article = nl_featured[0] if nl_featured else None

            # featured_article (a featured section in the category)
            try:
                featured_section, days_ago = settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS[category_slug]
                featured_article = category.section_set.get(slug=featured_section).latest_article()[0]
                assert (featured_article.date_published >= datetime.now() - timedelta(days_ago))
            except (KeyError, Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError, AssertionError):
                featured_article = None

            if export_context:
                export_ctx['articles'] = [
                    (
                        t[0].nl_serialize(position == 0), {'name': t[1].name, 'slug': t[1].slug}
                    ) for position, t in enumerate(top_articles)
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
            if as_news:
                receivers = receivers.filter(allow_news=True).exclude(category_newsletters__slug=category_slug)
            else:
                receivers = receivers.filter(category_newsletters__slug=category_slug)
            receivers = receivers.exclude(user__email__in=blocklisted)
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
        if as_news:
            list_id = 'novedades <%s>' % settings.SITE_DOMAIN
        else:
            list_id = '%s <%s.%s>' % (category_slug, __name__, settings.SITE_DOMAIN)
        ga_property_id = getattr(settings, 'GA_PROPERTY_ID', None)
        custom_subject = category.newsletter_automatic_subject is False and category.newsletter_subject
        email_subject = custom_subject or (
            getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_PREFIX', {}).get(category_slug, '')
        )
        if not custom_subject:
            subject_call = getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_CALLABLE', {}).get(category_slug)
            email_subject += \
                locate(subject_call)() if subject_call else remove_markup(getattr(cover_article, "headline", ""))

        email_from = (
            site.name if category_slug in getattr(
                settings, 'CORE_CATEGORY_NL_FROM_NAME_SITEONLY', ()
            ) else ('%s %s' % (site.name, category.name)),
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
                    'featured_article': featured_article.nl_serialize(True) if featured_article else None,
                }
            )
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

    # connect to smtp servers and send the emails
    smtp_servers = []
    if not(no_deliver or export_only):
        for alt_index in range(len(getattr(settings, "EMAIL_ALTERNATIVE", [])) + 1):
            smtp_servers.append(smtp_connect(alt_index))
        if not any(smtp_servers):
            # At least 1 smtp server must be available
            log.error("All MTA down, '%s %s' was used for partitions and mod" % (partitions, mod))
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
                        next(subscribers_iter)
                    )
                    is_subscriber = eval(is_subscriber)
                    is_subscriber_any = eval(is_subscriber_any)
                    is_subscriber_default = eval(is_subscriber_default)
                else:
                    s, is_subscriber = next(subscribers_iter)
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
                if as_news:
                    unsubscribe_url = '%s/usuarios/perfil/disable/allow_news/%s/' % (site_url, hashed_id)
                else:
                    unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
                        '&utm_campaign=%s&utm_content=unsubscribe' % (
                            site_url, category_slug, hashed_id, category_slug
                        )
                headers['List-Unsubscribe'] = headers['List-Unsubscribe-Post'] = '<%s>' % unsubscribe_url
                context.update(
                    {
                        "as_news": as_news,
                        'hashed_id': hashed_id,
                        'unsubscribe_url': unsubscribe_url,
                        'browser_preview_url': '%s/area/%s/nl/%s/' % (site_url, category_slug, hashed_id),
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
                send_result, smtp_index_choosed = None, None
                try:
                    if not no_deliver:
                        smtp_index_choosed = smtp_server_choice(s_user_email, smtp_servers)
                        if smtp_index_choosed is None:
                            send_result = "No SMTP server available"
                        else:
                            send_result = smtp_servers[smtp_index_choosed].sendmail(
                                settings.NEWSLETTERS_FROM_MX, [s_user_email], msg.as_string()
                            )
                        assert not send_result
                    log.info(
                        "%sEmail %s to %ssubscriber %s\t%s" % (
                            "(mod %d) " % mod if mod is not None else "",
                            'simulated' if no_deliver else 'sent(%s)' % (
                                ("A%d" % smtp_index_choosed) if smtp_index_choosed else "M"
                            ),
                            '' if is_subscriber else 'non-',
                            s_id,
                            s_user_email,
                        )
                    )
                    if is_subscriber:
                        subscriber_sent += 1
                    else:
                        user_sent += 1
                except AssertionError:
                    if not no_deliver:
                        log.error(
                            "Delivery errors for %ssubscriber %s: %s" % (
                                '' if is_subscriber else 'non-', s_id, send_result
                            )
                        )
                        # TODO: retry?
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
                        if smtp_index_choosed is not None:
                            smtp_servers[smtp_index_choosed] = smtp_connect(smtp_index_choosed)
                    except error:
                        log.warning('MTA reconnect failed')
                except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
                    # This means that is very probabble that this server will not work at all for any iteration, so we
                    # will remove it from the available servers list and retry this delivery if possible.
                    # If no available servers left, raise smth that can be handled by the next except to print&break
                    # TODO: do this
                    pass
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
            smtp_quit(smtp_servers)

        # update log stats counters only if subscriber_ids not given
        if not subscriber_ids:
            try:
                nl_delivery, created = NewsletterDelivery.objects.get_or_create(
                    delivery_date=today, newsletter_name=category_slug
                )
                nl_delivery.user_sent = (nl_delivery.user_sent or 0) + user_sent
                nl_delivery.subscriber_sent = (nl_delivery.subscriber_sent or 0) + subscriber_sent
                nl_delivery.user_refused = (nl_delivery.user_refused or 0) + user_refused
                nl_delivery.subscriber_refused = (nl_delivery.subscriber_refused or 0) + subscriber_refused
                nl_delivery.save()
            except Exception as e:
                log.error('Delivery stats not updated: %s' % e)

        log.info(
            '%s%s stats: user_sent: %d, subscriber_sent: %s, user_refused: %d, subscriber_refused: %d' % (
                "(mod %d) " % mod if mod is not None else "",
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
        parser.add_argument('category_slug', nargs=1, type=str)
        parser.add_argument('subscriber_ids', nargs='*', type=int)
        parser.add_argument(
            '--no-deliver',
            action='store_true',
            default=False,
            dest='no_deliver',
            help='Do not send the emails, only log',
        )
        parser.add_argument(
            '--offline',
            action='store_true',
            default=False,
            dest='offline',
            help='Do not use the database to fetch email data, get it from datasets previously generated',
        )
        parser.add_argument(
            '--as-news',
            action='store_true',
            default=False,
            dest='as_news',
            help='Send only to those who have "allow news" prop. activated and are not subscribed to this newsletter',
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
            type=str,
            dest='starting_from_s',
            help='Send to subscribers only if their email is alphabetically greater than',
        )
        parser.add_argument(
            '--starting-from-ns',
            action='store',
            type=str,
            dest='starting_from_ns',
            help='Send to non-subscribers only if their email is alphabetically greater than',
        )
        parser.add_argument(
            '--partitions',
            action='store',
            type=int,
            dest='partitions',
            help='Used with --mod, divide receipts in this quantity of partitions e.g.: --partitions=5',
        )
        parser.add_argument(
            '--mod',
            action='store',
            type=int,
            dest='mod',
            help='When --partitions is set, only take receipts whose id MOD partitions == this value e.g.: --mod=0',
        )
        parser.add_argument(
            '--hide-after-content-block',
            action='store_true',
            default=False,
            dest='hide_after_content_block',
            help='Hide after_content block in the newsletter template',
        )

    def handle(self, *args, **options):
        partitions, mod, offline = options.get('partitions'), options.get('mod'), options.get('offline')
        export_subscribers, export_context = options.get('export_subscribers'), options.get('export_context')
        export_only = export_subscribers or export_context
        if offline and export_only:
            raise CommandError('--export-* options can not be used with --offline')
        if partitions is None and mod is not None or mod is None and partitions is not None:
            raise CommandError('--partitions must be used with --mod')
        category_slug = options.get('category_slug')[0]
        try:
            no_deliver = options.get('no_deliver')
            category = category_slug if offline else Category.objects.get(slug=category_slug)
        except Category.DoesNotExist:
            raise CommandError('No category matching the slug given found')
        as_news = options.get("as_news")
        if not export_only:
            h = logging.FileHandler(
                filename=settings.SENDNEWSLETTER_LOGFILE % (
                    category_slug + ("_as_news" if as_news else ""), today.strftime('%Y%m%d')
                )
            )
            h.setFormatter(log_formatter)
            log.addHandler(h)
            start_time = time.time()
        build_and_send(
            category,
            no_deliver,
            offline,
            as_news,
            export_subscribers,
            export_context,
            options.get('site_id'),
            options.get('starting_from_s'),
            options.get('starting_from_ns'),
            partitions,
            mod,
            options.get('subscriber_ids'),
            options.get('hide_after_content_block'),
        )
        if not export_only:
            log.info(
                "%s%s completed in %.0f seconds" % (
                    "(mod %d) " % mod if mod is not None else "",
                    'Simulation' if no_deliver else 'Delivery',
                    time.time() - start_time,
                )
            )
