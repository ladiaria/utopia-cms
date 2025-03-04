# -*- coding: utf-8 -*-
# utopia-cms, 2018-2024, Aníbal Pacheco
# TODO: Alert when exporting context and exists a due already-prepared NL (abort or continue only if a new command arg
#       "ignore-due" was passed). Find a better name for this new arg.

from builtins import next

from os.path import basename, join
import logging
import locale
import json
from csv import reader, writer
from pydoc import locate
from MySQLdb import ProgrammingError
from hashids import Hashids
from email.utils import make_msgid
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.db import OperationalError
from django.core.management.base import CommandError
from django.template import Engine, Context
from django.contrib.sites.models import Site
from django.utils import translation
from django.utils.timezone import now, datetime

from apps import blocklisted
from core.models import Category, CategoryNewsletter, CategoryHome, Article, get_latest_edition
from core.utils import get_category_template, get_nl_featured_article_id, nl_utm_params, format_nl_date
from core.templatetags.ldml import remove_markup
from thedaily.models import Subscriber
from thedaily.utils import subscribers_nl_iter, subscribers_nl_iter_filter
from libs.utils import smtp_connect, nl_serialize_multi

from . import SendNLCommand


# CFG
EMAIL_ATTACH, ATTACHMENTS = True, []

# log
log = logging.getLogger(__name__)

# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


class Command(SendNLCommand):
    help = 'Sends the last category newsletter by email to all subscribers of the category given or those given by id.'
    nl_date = None

    def add_arguments(self, parser):
        parser.add_argument('category_slug', nargs=1, type=str)
        parser.add_argument(
            '--site-id',
            action='store',
            type=int,
            dest='site_id',
            help='Use another site instead of the current site to build the URLs inside the message',
        )
        parser.add_argument(
            '--nl-date',
            action='store',
            type=str,
            dest='nl_date',
            help='Date shown in the newsletter content header: YYYY-mm-dd (default: today)',
        )
        parser.add_argument(
            '--hide-after-content-block',
            action='store_true',
            default=False,
            dest='hide_after_content_block',
            help='Hide after_content block in the newsletter template',
        )
        super().add_arguments(parser)

    def build_and_send(self):
        locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)
        export_ctx = self.default_common_ctx.copy()
        export_ctx.update(
            {
                'newsletter_campaign': self.category_slug,
                'nl_date': format_nl_date(self.nl_date),
                'hide_after_content_block': self.hide_after_content_block,
                'newsletter_name': self.category.newsletter_name,
                "newsletter_header_color": self.category.newsletter_header_color,
            }
        )
        export_ctx.update(self.newsletter_extra_context)
        context = export_ctx.copy()

        try:

            offline_ctx_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_ctx.json' % self.category_slug)
            offline_csv_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_subscribers.csv' % self.category_slug)
            if self.offline:
                try:
                    context = json.loads(open(offline_ctx_file).read())
                except FileNotFoundError as fnfe_exc:
                    log.error("Offline context missing, tip: you can create it using --export-context option")
                    raise CommandError(fnfe_exc)
                # de-serialize dates
                cover_article = context['cover_article']
                if cover_article:
                    dp_cover = datetime.strptime(cover_article['date_published'], '%Y-%m-%d').date()
                    context['cover_article']['date_published'] = dp_cover
                featured_article = context['featured_article']
                if featured_article:
                    dp_featured = datetime.strptime(featured_article['date_published'], '%Y-%m-%d').date()
                    context['featured_article']['date_published'] = dp_featured
                dp_articles = []
                for a in context['articles']:
                    dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
                    a['date_published'] = dp_article
                    dp_articles.append((a, False))
                context['articles'] = dp_articles
                if 'featured_articles' in context:
                    dp_featured_articles = []
                    for a in context['featured_articles']:
                        dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
                        a['date_published'] = dp_article
                        dp_featured_articles.append(a)
                    context['featured_articles'] = dp_featured_articles
            elif not self.export_subscribers or self.export_context:
                category_nl = CategoryNewsletter.objects.get(category=self.category, valid_until__gt=now())
                cover_article, featured_article = category_nl.cover(), category_nl.featured_article()
                if self.export_context:
                    export_ctx.update(
                        {
                            'articles': [
                                a.nl_serialize(
                                    position == 0, category=self.category
                                ) for position, a in enumerate(category_nl.non_cover_articles())
                            ],
                            'featured_articles': nl_serialize_multi(category_nl.featured_articles(), self.category),
                        }
                    )
                else:
                    context.update(
                        {
                            'articles': nl_serialize_multi(
                                [(a, False) for a in category_nl.non_cover_articles()], self.category, dates=False
                            ),
                            'featured_articles': nl_serialize_multi(
                                category_nl.featured_articles(), self.category, dates=False
                            ),
                        }
                    )

        except CategoryNewsletter.DoesNotExist:

            if not (self.offline or self.export_subscribers) or self.export_context:
                try:
                    cover_article = self.category.home.cover()
                except CategoryHome.DoesNotExist as dne:
                    raise CommandError(dne)
                cover_article_section = cover_article.get_section(self.category) if cover_article else None
                top_articles = [(a, False) for a in self.category.home.non_cover_articles()]

                listonly_section = getattr(
                    settings, 'CORE_CATEGORY_NEWSLETTER_LISTONLY_SECTIONS', {}
                ).get(self.category_slug)
                if listonly_section:
                    top_articles = [t for t in top_articles if getattr(t[0].section, "slug", None) == listonly_section]
                    if getattr(cover_article_section, "slug", None) != listonly_section:
                        cover_article = top_articles.pop(0)[0] if top_articles else None

                # featured directly by article.id in settings/edition
                featured_article_id = get_nl_featured_article_id()
                if featured_article_id:
                    nl_featured = Article.objects.filter(id=featured_article_id)
                else:
                    latest_edition = get_latest_edition()
                    nl_featured = latest_edition.newsletter_featured_articles() if latest_edition else None
                opinion_article = nl_featured[0] if nl_featured else None

                # featured articles by featured section in the category (by settings)
                # TODO: support to use more than one
                featured_article = self.category.nl_featured_section_articles().first()

                if self.export_context:
                    export_ctx.update(
                        {
                            'opinion_article': nl_serialize_multi(opinion_article, self.category, True),
                            'articles': [
                                t[0].nl_serialize(position == 0, category=self.category)
                                for position, t in enumerate(top_articles)
                            ],
                        }
                    )
                else:
                    context.update(
                        {
                            'opinion_article': nl_serialize_multi(opinion_article, self.category, True, False),
                            'articles': nl_serialize_multi(top_articles, self.category, dates=False),
                        }
                    )

        # any custom attached files
        # TODO: make this a feature in the admin using adzone also make it path-setting instead of absolute
        # f_ads = ['/srv/ldsocial/portal/media/document.pdf']
        f_ads = []

        if not self.offline:
            # TODO: extra arg to include more kwargs to this next line filter
            receivers = Subscriber.objects.filter(user__is_active=True).exclude(user__email='')
            if self.subscriber_ids:
                receivers = receivers.filter(id__in=self.subscriber_ids)
            else:
                if self.as_news:
                    receivers = receivers.filter(
                        allow_news=True
                    ).exclude(category_newsletters__slug=self.category_slug)
                else:
                    receivers = receivers.filter(category_newsletters__slug=self.category_slug)
                receivers = receivers.exclude(user__email__in=blocklisted)
                # if both "starting_from" we can filter now with the minimum
                if self.starting_from_s and self.starting_from_ns:
                    receivers = receivers.filter(user__email__gt=min(self.starting_from_s, self.starting_from_ns))
                if self.partitions is not None and self.mod is not None:
                    receivers = receivers.extra(
                        where=['MOD(%s.id,%d)=%d' % (Subscriber._meta.db_table, self.partitions, self.mod)]
                    )

        if self.offline:
            custom_subject = context['custom_subject']
            email_subject = context['email_subject']
            email_from = context['email_from']
            site_url = context['site_url']
            list_id = context['list_id']
            try:
                r = reader(open(offline_csv_file))
            except FileNotFoundError as fnfe_exc:
                log.error("Offline receipts csv missing, tip: you can create it using --export-subscribers option")
                raise CommandError(fnfe_exc)
            if self.subscriber_ids:
                subscribers_iter = subscribers_nl_iter_filter(r, lambda row: int(row[0]) in self.subscriber_ids)
            elif self.partitions is not None and self.mod is not None:
                subscribers_iter = subscribers_nl_iter_filter(r, lambda row: int(row[0]) % self.partitions == self.mod)
            else:
                subscribers_iter = r
        elif not self.export_subscribers or self.export_context:
            site_url = settings.SITE_URL_SD
            if self.as_news:
                list_id = 'novedades <%s>' % settings.SITE_DOMAIN
            else:
                list_id = '%s <%s.%s>' % (self.category_slug, __name__, settings.SITE_DOMAIN)
            custom_subject = self.category.newsletter_automatic_subject is False and self.category.newsletter_subject
            email_subject = custom_subject or (
                getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_PREFIX', {}).get(self.category_slug, '')
            )
            if not custom_subject:
                subject_call = getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_CALLABLE', {}).get(self.category_slug)
                email_subject += \
                    locate(subject_call)() if subject_call else remove_markup(getattr(cover_article, "nl_title", ""))

            # TODO: encapsulate this in a Category model method
            email_from = (
                self.category.newsletter_from_name or (
                    self.site.name if self.category_slug in getattr(
                        settings, 'CORE_CATEGORY_NL_FROM_NAME_SITEONLY', ()
                    ) else ('%s %s' % (self.site.name, self.category.name))
                ),
                self.category.newsletter_from_email or settings.NOTIFICATIONS_FROM_ADDR1,
            )

        translation.activate(settings.LANGUAGE_CODE)

        if not self.export_subscribers or self.export_context:
            common_ctx = {'site_url': site_url, 'custom_subject': custom_subject}
        if self.export_only:
            if self.export_context:
                export_ctx.update(common_ctx)
                export_ctx.update(
                    {
                        'email_subject': email_subject,
                        'email_from': email_from,
                        'list_id': list_id,
                        'cover_article': nl_serialize_multi(cover_article, self.category, True),
                        'featured_article': nl_serialize_multi(featured_article, self.category, True),
                    }
                )
                open(offline_ctx_file, 'w').write(json.dumps(export_ctx))
            if self.export_subscribers:
                export_subscribers_writer = writer(open(offline_csv_file, 'w'))
            else:
                return
        else:
            common_headers = {'List-ID': list_id, "Return-Path": settings.NEWSLETTERS_FROM_MX}
            if not self.offline:
                context.update(common_ctx)
                context.update(
                    {
                        'cover_article': nl_serialize_multi(cover_article, self.category, True, False),
                        'featured_article': nl_serialize_multi(featured_article, self.category, True, False),
                    }
                )

        if not self.offline:
            subscribers_iter = subscribers_nl_iter(receivers, self.starting_from_s, self.starting_from_ns)

        # connect to smtp servers
        if not (self.no_deliver or self.export_only):
            for alt_index in range(len(getattr(settings, "EMAIL_ALTERNATIVE", [])) + 1):
                self.smtp_servers.append(smtp_connect(alt_index))
            if not any(self.smtp_servers):
                # At least 1 smtp server must be available
                log.error("All MTA down, '%s %s' was used for partitions and mod" % (self.partitions, self.mod))
                return

        s_id, is_subscriber, nl_delivery_date = None, None, self.nl_delivery_dt.strftime("%Y%m%d")
        email_template = Engine.get_default().get_template(get_category_template(self.category_slug, "newsletter"))

        while True:

            try:
                if not self.retry_last_delivery:
                    if self.offline:
                        (
                            s_id,
                            s_name,
                            s_user_email,
                            hashed_id,
                            is_subscriber,
                            is_subscriber_any,
                            is_subscriber_default,
                        ) = next(subscribers_iter)
                        is_subscriber = eval(is_subscriber)
                        is_subscriber_any = eval(is_subscriber_any)
                        is_subscriber_default = eval(is_subscriber_default)
                    else:
                        s, is_subscriber = next(subscribers_iter)
                        s_id, s_name, s_user_email = s.id, s.get_full_name(), s.user.email
                        hashed_id = hashids.encode(int(s_id))
                        is_subscriber_any = s.is_subscriber_any()
                        is_subscriber_default = s.is_subscriber(settings.DEFAULT_PUB)

                if self.export_subscribers:
                    export_subscribers_writer.writerow(
                        [
                            s_id,
                            s_name,
                            s_user_email,
                            hashed_id,
                            is_subscriber,
                            is_subscriber_any,
                            is_subscriber_default,
                        ]
                    )
                elif not self.export_context:

                    if self.as_news:
                        unsubscribe_url = '%s/usuarios/perfil/disable/allow_news/%s/' % (site_url, hashed_id)
                    else:
                        unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/%s' % (
                            site_url, self.category_slug, hashed_id, nl_utm_params(self.category_slug)
                        )

                    if self.force_no_subscriber:
                        is_subscriber = is_subscriber_any = is_subscriber_default = False
                    context.update(
                        {
                            "as_news": self.as_news,
                            'hashed_id': hashed_id,
                            'unsubscribe_url': unsubscribe_url,
                            'browser_preview_url': '%s/area/%s/nl/%s/' % (site_url, self.category_slug, hashed_id),
                            'subscriber_id': s_id,
                            'is_subscriber': is_subscriber,
                            'is_subscriber_any': is_subscriber_any,
                            'is_subscriber_default': is_subscriber_default,
                            "track_open_event_url": "%s/usuarios/nl_track/%c_%s_%s_%s.gif" % (
                                site_url,
                                "s" if is_subscriber else "r",
                                hashed_id,
                                self.category_slug,
                                nl_delivery_date,
                            ),
                        }
                    )

                    headers = common_headers.copy()
                    headers['Message-Id'] = make_msgid(str(s_id))
                    headers['List-Unsubscribe'] = '<%s>' % unsubscribe_url
                    headers['List-Unsubscribe-Post'] = "List-Unsubscribe=One-Click"

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

                    self.sendmail(s_user_email, log, msg, is_subscriber, s_id)
                    if not (self.no_deliver or any(self.smtp_servers)):
                        log.error(
                            "All MTA down, (%s, %s, %s, %s) was the last delivery attempt" % (
                                s_user_email if s_id else None, is_subscriber, self.partitions, self.mod
                            )
                        )
                        # TODO: here we can try only once to reconnect all servers again (this scenario can be
                        #       reproduced with stop and continue the process after half/one hour using
                        #       "kill -[STOP|CONT] <pid>")
                        break

            except (ProgrammingError, OperationalError, StopIteration) as exc:
                # the connection to databse can be killed, if that is the case print useful log to continue
                if isinstance(exc, (ProgrammingError, OperationalError)):
                    log.error(
                        'DB connection error, (%s, %s, %s, %s) was the last delivery attempt' % (
                            s_user_email if s_id else None, is_subscriber, self.partitions, self.mod
                        )
                    )
                break

    def handle(self, *args, **options):
        self.category_slug = options.get('category_slug')[0]
        if self.category_slug in getattr(settings, "SENDNEWSLETTER_CATEGORY_DISALLOW_DEFAULT_CMD", ()):
            raise CommandError("The newsletter of this category is not allowed to be sent using this command")
        self.load_options(options)
        try:
            nl_date = options.get('nl_date')
            self.nl_date = datetime.strptime(nl_date, '%Y-%m-%d').date() if nl_date else self.nl_delivery_dt
        except ValueError:
            raise CommandError("Invalid date format for argument --nl-date, use YYYY-mm-dd")
        self.hide_after_content_block = options.get('hide_after_content_block')
        try:
            c = Category.objects.get(slug=self.category_slug)
            self.category = self.category_slug if self.offline else c
            self.newsletter_extra_context = c.nl_serialize()
            self.newsletter_extra_context.update(c.newsletter_extra_context)
        except Category.DoesNotExist:
            raise CommandError('No category matching the given slug found')
        self.initlog(log, self.category_slug)
        site_id = options.get("site_id")
        self.site = Site.objects.get(id=site_id) if site_id else Site.objects.get_current()
        self.build_and_send()
        self.finish(log, self.category_slug)
