# -*- coding: utf-8 -*-
# utopia-cms, 2018-2023, Aníbal Pacheco
from __future__ import unicode_literals

from builtins import next

import sys
from os.path import basename, join
import logging
import locale
import time
import json
from datetime import date, datetime, timedelta
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

from apps import blocklisted
from core.models import Category, CategoryNewsletter, Section, Article, get_latest_edition
from core.templatetags.ldml import remove_markup
from thedaily.models import Subscriber
from thedaily.utils import subscribers_nl_iter, subscribers_nl_iter_filter
from libs.utils import smtp_connect

from . import SendNLCommand


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


class Command(SendNLCommand):
    help = 'Sends the last category newsletter by email to all subscribers of the category given or those given by id.'

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
            '--hide-after-content-block',
            action='store_true',
            default=False,
            dest='hide_after_content_block',
            help='Hide after_content block in the newsletter template',
        )
        super().add_arguments(parser)

    def build_and_send(self):
        locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)
        export_ctx = {
            'newsletter_campaign': self.category_slug,
            'nl_date': "{d:%A} {d.day} de {d:%B de %Y}".format(d=today).capitalize(),
            'hide_after_content_block': self.hide_after_content_block,
        }
        context = export_ctx.copy()
        context['category'] = self.category

        try:

            offline_ctx_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_ctx.json' % self.category_slug)
            offline_csv_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_subscribers.csv' % self.category_slug)
            if self.offline:
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
                    dp_articles.append((a, False, a_section))
                context['articles'] = dp_articles
                if 'featured_articles' in context:
                    dp_featured_articles = []
                    for a, a_section in context['featured_articles']:
                        dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
                        a['date_published'] = dp_article
                        dp_featured_articles.append((a, a_section))
                    context['featured_articles'] = dp_featured_articles
            elif not self.export_subscribers or self.export_context:
                category_nl = CategoryNewsletter.objects.get(category=self.category, valid_until__gt=datetime.now())
                cover_article, featured_article = category_nl.cover(), category_nl.featured_article()
                featured_article_section = featured_article.publication_section() if featured_article else None
                if self.export_context:
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
                            'cover_article_section':
                                cover_article.publication_section().name if cover_article else None,
                            'articles':
                                [(a, a.publication_section()) for a in category_nl.non_cover_articles()],
                            'featured_article_section': featured_article_section,
                            'featured_articles':
                                [(a, a.publication_section()) for a in category_nl.non_cover_featured_articles()],
                        }
                    )

        except CategoryNewsletter.DoesNotExist:

            if not (self.offline or self.export_subscribers) or self.export_context:
                cover_article = self.category.home.cover()
                cover_article_section = cover_article.publication_section() if cover_article else None
                top_articles = [(a, a.publication_section()) for a in self.category.home.non_cover_articles()]

                listonly_section = getattr(
                    settings, 'CORE_CATEGORY_NEWSLETTER_LISTONLY_SECTIONS', {}
                ).get(self.category_slug)
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
                    featured_section, days_ago = \
                        settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS[self.category_slug]
                    featured_article = self.category.section_set.get(slug=featured_section).latest_article()[0]
                    assert (featured_article.date_published >= datetime.now() - timedelta(days_ago))
                except (KeyError, Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError, AssertionError):
                    featured_article = None

                if self.export_context:
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

        if not self.offline:
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
                    receivers = receivers.extra(where=['MOD(%s.id,%d)=%d' % (Subscriber._meta.db_table, self.partitions, self.mod)])

        if self.offline:
            custom_subject = context['custom_subject']
            email_subject = context['email_subject']
            email_from = context['email_from']
            site_url = context['site_url']
            list_id = context['list_id']
            ga_property_id = context['ga_property_id']
            r = reader(open(offline_csv_file))
            if self.subscriber_ids:
                subscribers_iter = subscribers_nl_iter_filter(r, lambda row: int(row[0]) in self.subscriber_ids)
            elif self.partitions is not None and self.mod is not None:
                subscribers_iter = subscribers_nl_iter_filter(r, lambda row: int(row[0]) % self.partitions == self.mod)
            else:
                subscribers_iter = r
        elif not self.export_subscribers or self.export_context:
            site_url = '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN)
            if self.as_news:
                list_id = 'novedades <%s>' % settings.SITE_DOMAIN
            else:
                list_id = '%s <%s.%s>' % (self.category_slug, __name__, settings.SITE_DOMAIN)
            ga_property_id = getattr(settings, 'GA_PROPERTY_ID', None)
            custom_subject = self.category.newsletter_automatic_subject is False and self.category.newsletter_subject
            email_subject = custom_subject or (
                getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_PREFIX', {}).get(self.category_slug, '')
            )
            if not custom_subject:
                subject_call = getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_CALLABLE', {}).get(self.category_slug)
                email_subject += \
                    locate(subject_call)() if subject_call else remove_markup(getattr(cover_article, "headline", ""))

            email_from = (
                self.site.name if self.category_slug in getattr(
                    settings, 'CORE_CATEGORY_NL_FROM_NAME_SITEONLY', ()
                ) else ('%s %s' % (self.site.name, self.category.name)),
                settings.NOTIFICATIONS_FROM_ADDR1,
            )

        translation.activate(settings.LANGUAGE_CODE)

        if not self.export_subscribers or self.export_context:
            common_ctx = {'site_url': site_url, 'ga_property_id': ga_property_id, 'custom_subject': custom_subject}
        if self.export_only:
            if self.export_context:
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
            if self.export_subscribers:
                export_subscribers_writer = writer(open(offline_csv_file, 'w'))
            else:
                return
        else:
            common_headers = {'List-ID': list_id, "Return-Path": settings.NEWSLETTERS_FROM_MX}
            if not self.offline:
                context.update(common_ctx)
                context.update({'cover_article': cover_article, 'featured_article': featured_article})

        if not self.offline:
            subscribers_iter = subscribers_nl_iter(receivers, self.starting_from_s, self.starting_from_ns)

        # connect to smtp servers
        if not(self.no_deliver or self.export_only):
            for alt_index in range(len(getattr(settings, "EMAIL_ALTERNATIVE", [])) + 1):
                self.smtp_servers.append(smtp_connect(alt_index))
            if not any(self.smtp_servers):
                # At least 1 smtp server must be available
                log.error("All MTA down, '%s %s' was used for partitions and mod" % (self.partitions, self.mod))
                return

        s_id, is_subscriber = None, None
        email_template = Engine.get_default().get_template(
            '%s/newsletter/%s.html' % (settings.CORE_CATEGORIES_TEMPLATE_DIR, self.category_slug)
        )

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
                        s_id, s_name, s_user_email = s.id, s.name, s.user.email
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
                        unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
                            '&utm_campaign=%s&utm_content=unsubscribe' % (
                                site_url, self.category_slug, hashed_id, self.category_slug
                            )

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
                        }
                    )

                    headers = common_headers.copy()
                    headers['Message-Id'] = make_msgid(str(s_id))
                    headers['List-Unsubscribe'] = headers['List-Unsubscribe-Post'] = '<%s>' % unsubscribe_url

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
        self.hide_after_content_block = options.get('hide_after_content_block')
        try:
            self.category = self.category_slug if self.offline else Category.objects.get(slug=self.category_slug)
        except Category.DoesNotExist:
            raise CommandError('No category matching the slug given found')
        if not self.export_only:
            h = logging.FileHandler(
                filename=settings.SENDNEWSLETTER_LOGFILE % (
                    self.category_slug + ("_as_news" if self.as_news else ""), today.strftime('%Y%m%d')
                )
            )
            h.setFormatter(log_formatter)
            log.addHandler(h)
            self.start_time = time.time()
        site_id = options.get("site_id")
        self.site = Site.objects.get(id=site_id) if site_id else Site.objects.get_current()
        self.build_and_send()
        self.finish(log, self.category_slug)
