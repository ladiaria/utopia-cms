from builtins import next
from os.path import basename, join
import logging
import json
from sorl.thumbnail import get_thumbnail
from csv import reader, writer
from MySQLdb import ProgrammingError
from email.utils import make_msgid
from emails.django import DjangoMessage as Message
from hashids import Hashids

from django.conf import settings
from django.db import OperationalError
from django.db.models import Q
from django.core.management import CommandError
from django.core.validators import validate_email
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.template import Engine, Context
from django.contrib.sites.models import Site
from django.utils import translation
from django.utils.timezone import datetime, make_naive

from apps import blocklisted
from libs.utils import smtp_connect
from core.models import Publication, Article, Edition, DefaultNewsletter
from core.views.publication import nl_template_name
from core.templatetags.ldml import remove_markup
from core.utils import serialize_wrapper, get_nl_featured_article_id
from thedaily.models import Subscriber
from thedaily.utils import subscribers_nl_iter_filter
from . import SendNLCommand


# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


class Command(SendNLCommand):
    # TODO: idea to implement direct email address receipts:
    #       - if all args are integers => they are subscriber_ids
    #       - elif all args are emails => direct email address receipts
    help = """
        Sends the default publication's newsletter (or the newsletter of the publication given by slug) to all
        subscribers, or to those given by id.
    """
    nlobj_pubs = (settings.DEFAULT_PUB,)  # The slugs of the publications that have a custom NL Model.

    # Allow to choose the latest edition if no today edition found (for the pubs in nlobj_pubs only).
    nlobj_pubs_edition_use_latest = True

    # A way to disallow this base command to be used for some publications. (to be overriden in child commands)
    disallowed_publications = getattr(settings, "CORE_PUBLICATIONS_NL_DISALLOW_BASE_CMD", ())

    edition, nlobj, subscriber_extra_info_keys, log = None, None, (), logging.getLogger(__name__)

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--edition-date',
            action='store',
            type=str,
            dest='edition_date',
            help='Date of the edition to send: YYYY-mm-dd',
        )
        parser.add_argument(
            '--only-supplements',
            action='store_true',
            dest='only_supplements',
            default=False,
            help='Send only supplements to PDF subscribers',
        )
        parser.add_argument(
            '--site-id',
            action='store',
            type=int,
            dest='site_id',
            help='Use another site instead of the current site to build the URLs inside the message',
        )
        parser.add_argument(
            '--publication',
            action='store',
            type=str,
            default=settings.DEFAULT_PUB,
            dest='publication_slug',
            help='Use another publication instead the default one',
        )

    def get_template_name(self, default=None):
        return nl_template_name(self.pub_slug, **({"default": default} if default else {}))

    def get_publication(self):
        if self.offline:
            return self.edition['publication']
        elif self.edition:
            return self.edition.publication
        else:
            return Publication.objects.get(slug=self.pub_slug)

    def default_receivers(self, receivers):
        return receivers.filter(Q(newsletters__slug=self.pub_slug) | Q(user__is_staff=True))

    def extra_context(self):
        return {}

    def get_edition_cover_url(self):
        if self.edition.cover_image_file_exists():
            return get_thumbnail(self.edition.cover, '204x500').url
        elif settings.DEBUG:
            self.log.warn("Edición sin imagen de portada")

    def msg_attach_file(self, msg, filename):
        try:
            msg.attach(filename=basename(filename), data=open(filename, "rb"))
        except FileNotFoundError as fnfe:
            if settings.DEBUG:
                self.log.warn(fnfe)

    def is_subscriber(self, subscriber):
        return subscriber.is_subscriber(self.pub_slug)

    def subscriber_extra(self, extra):
        return dict(
            zip(
                self.subscriber_extra_info_keys,
                extra if self.offline else (extra.get(key) for key in self.subscriber_extra_info_keys),
            )
        )

    def send_subscribers_mail(self):
        site = Site.objects.get(id=self.site_id) if self.site_id else Site.objects.get_current()
        export_ctx, common_ctx = Publication.objects.get(slug=self.pub_slug).extra_context.copy(), {}
        # A flag to force no delivery can be set in extra context
        if export_ctx.get("force_no_delivery"):
            self.log.info("Force to no delivery by the publication extra context, aborting.")
            return
        export_ctx.update({"as_news": self.as_news})
        context = export_ctx.copy()

        # any custom attached files
        # TODO: make this a feature in the admin using adzone also make it path-setting instead of absolute
        # f_ads = ['/srv/ldsocial/portal/media/document.pdf']
        f_ads = []

        if not self.offline:
            # All subscribers with an active user and (receive the newsletter or the pdf or are in a route that is
            # "tagged[*]" to send pdf or are staff). [*] Feature only available for the default pub.
            # Then, excluding those who have a blank email or are present in a blocklist.
            # If subscriber_ids are given by param, then force the sending only to them.
            # If only_supplements, send only supplements to PDF subscribers only.
            # Special "as_news" delivery is useful for the first delivery of a brand new NL. (TODO: document this)
            receivers = Subscriber.objects.filter(user__is_active=True).exclude(user__email='')
            if self.subscriber_ids:
                receivers = receivers.filter(id__in=self.subscriber_ids)
            else:
                if self.as_news:
                    receivers = receivers.filter(allow_news=True).exclude(newsletters__slug=self.pub_slug)
                else:
                    receivers = receivers.filter(newsletters__slug=self.pub_slug)
                receivers = receivers.exclude(user__email__in=blocklisted)
                if self.only_supplements:
                    if hasattr(self, 'only_supplement_receivers'):
                        receivers = self.only_supplement_receivers(receivers)
                else:
                    receivers = self.default_receivers(receivers)
                # if both "starting_from" we can filter now with the minimum
                if self.starting_from_s and self.starting_from_ns:
                    receivers = receivers.filter(user__email__gt=min(self.starting_from_s, self.starting_from_ns))
                if self.partitions is not None and self.mod is not None:
                    receivers = receivers.extra(
                        where=['MOD(%s.id,%d)=%d' % (Subscriber._meta.db_table, self.partitions, self.mod)]
                    )

        offline_ctx_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, self.pub_slug + '_ctx.json')
        offline_csv_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, self.pub_slug + '_subscribers.csv')
        try:
            publication = self.get_publication()
        except Publication.DoesNotExist:
            error_msg = "Aborting, no publicaytion with slug='%s' found." % self.pub_slug
            self.log.error(error_msg)
            raise CommandError(error_msg)
        if self.offline:
            try:
                context = json.loads(open(offline_ctx_file).read())
            except FileNotFoundError as fnfe_exc:
                self.log.error("Offline context missing, tip: you can create it using --export-context option")
                raise CommandError(fnfe_exc)
            edition_download_url = self.edition.get('download_url')
            email_subject, email_from_name = context['email_subject'], context['email_from_name']
            site_url = context['site_url']
            list_id = context['list_id']
            self.newsletter_campaign = publication['newsletter_campaign']
            context.update({'publication': publication, 'nl_date': self.edition['date_published']})
            # de-serialize dates
            dp_cover = datetime.strptime(context['cover_article']['date_published'], '%Y-%m-%d').date()
            context['cover_article']['date_published'] = dp_cover
            dp_articles = []
            try:
                # TODO: check if this try is needed in the other "send NL" management commads
                for a, include_photo in context['articles']:
                    dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
                    a['date_published'] = dp_article
                    dp_articles.append((a, include_photo))
            except ValueError:
                raise CommandError(
                    "Unable to deserialize context article data, a probabble reason can be it was serialized with an "
                    "old version of this script"
                )
            context['articles'] = dp_articles

            try:
                r = reader(open(offline_csv_file))
            except FileNotFoundError as fnfe_exc:
                self.log.error(
                    "Offline receipts csv missing, tip: you can create it using --export-subscribers option"
                )
                raise CommandError(fnfe_exc)
            if self.subscriber_ids:
                subscribers_iter = subscribers_nl_iter_filter(r, lambda row: int(row[0]) in self.subscriber_ids)
            elif self.partitions is not None and self.mod is not None:
                subscribers_iter = subscribers_nl_iter_filter(r, lambda row: int(row[0]) % self.partitions == self.mod)
            else:
                subscribers_iter = r
        else:
            site_url = f"{settings.URL_SCHEME}://{site.domain}"
            if not self.export_subscribers or self.export_context:
                # fixed email data
                self.newsletter_campaign = publication.newsletter_campaign
                common_ctx["logo_url"] = getattr(
                    publication.newsletter_logo or publication.image, 'url', '/static/img/logo-white.png'
                )
                if self.nlobj:
                    top_articles = [
                        (a.article, a.include_photo)
                        for a in self.nlobj.get_article_set().filter(article__is_published=True)
                    ]
                else:
                    top_articles = [(a, False) for a in self.edition.top_articles]

                if not top_articles:
                    self.log.error('Edición sin artículos de portada.')
                    return

                top_max = self.top_articles_max() if hasattr(self, 'top_articles_max') else None
                if top_max:
                    top_articles = top_articles[:top_max]

                cover_article = top_articles.pop(0)[0]  # pop cover from list

                if self.as_news:
                    list_id = 'novedades <%s>' % settings.SITE_DOMAIN
                else:
                    list_id = '%s <%s.%s>' % (self.newsletter_campaign, __name__, settings.SITE_DOMAIN)
                nl_featured_article_id = get_nl_featured_article_id()
                nl_featured = (
                    Article.objects.filter(id=nl_featured_article_id) if nl_featured_article_id
                    else self.edition.newsletter_featured_articles()
                )
                opinion_article = nl_featured[0] if nl_featured else None  # TODO: rename this variable better

                # get email from name
                if publication.slug in getattr(settings, 'CORE_PUBLICATIONS_NL_FROM_NAME_NAMEONLY', ()):
                    email_from_name = publication.name
                else:
                    try:
                        email_from_name = '%s %s' % (
                            Publication.objects.get(slug=settings.DEFAULT_PUB).name,
                            publication.newsletter_name or publication.name,
                        )
                    except Publication.DoesNotExist:
                        email_from_name = publication.newsletter_name or publication.name

                custom_subject = (publication.newsletter_automatic_subject is False and publication.newsletter_subject)
                custom_subject_prefix = self.custom_subject_prefix() if hasattr(self, 'custom_subject_prefix') else ""
                email_subject = custom_subject or (custom_subject_prefix + remove_markup(cover_article.nl_title()))
                edition_cover_url = self.get_edition_cover_url()
                edition_download_url = self.edition.get_download_url()

            # iterate over receivers and yield the subscribers first, saving the
            # not subscribers ids in a temporal list an then yield them also
            def subscribers():
                receivers2 = []
                for s in receivers.distinct().order_by('user__email').iterator():
                    if s.user.email:
                        # validate email before doing anything
                        try:
                            validate_email(s.user.email)
                        except ValidationError:
                            continue
                        if self.is_subscriber(s):
                            if (
                                not self.starting_from_s
                                or (self.starting_from_s and s.user.email > self.starting_from_s)
                            ):
                                yield s, True
                        else:
                            if (
                                not self.starting_from_ns
                                or (self.starting_from_ns and s.user.email > self.starting_from_ns)
                            ):
                                receivers2.append(s.id)
                for sus_id in receivers2:
                    try:
                        yield Subscriber.objects.get(id=sus_id), False
                    except Subscriber.DoesNotExist:
                        # rare, but could be recently deleted
                        continue

        translation.activate(settings.LANGUAGE_CODE)

        common_ctx['site_url'] = site_url
        context.update(common_ctx)

        if self.export_only:
            if self.export_context:
                export_ctx.update(common_ctx)
                export_ctx.update(
                    {
                        'newsletter_campaign': self.newsletter_campaign,
                        'custom_subject': custom_subject,
                        'edition_cover_url': edition_cover_url,
                        'articles': serialize_wrapper(top_articles, publication),
                        'list_id': list_id,
                        'cover_article': serialize_wrapper(cover_article, publication, True),
                        'opinion_article': serialize_wrapper(opinion_article, publication, True),
                        'email_from_name': email_from_name,
                        'email_subject': email_subject,
                    }
                )
                export_ctx.update(self.extra_context())
                open(offline_ctx_file, 'w').write(json.dumps(export_ctx))
            if self.export_subscribers:
                export_subscribers_writer = writer(open(offline_csv_file, 'w'))
            else:
                return
        else:
            common_headers = {'List-ID': list_id, "Return-Path": settings.NEWSLETTERS_FROM_MX}

        if not self.offline:
            if not self.export_subscribers:
                context.update(
                    {
                        'publication': publication,
                        'newsletter_campaign': self.newsletter_campaign,
                        'custom_subject': custom_subject,
                        'edition_cover_url': edition_cover_url,
                        'articles': serialize_wrapper(top_articles, publication, dates=False),
                        'nl_date': self.edition.date_published_verbose(False),
                        'cover_article': serialize_wrapper(cover_article, publication, True, False),
                        'opinion_article': serialize_wrapper(opinion_article, publication, True),
                    }
                )
                context.update(self.extra_context())
            subscribers_iter = subscribers()

        # connect to smtp servers
        if not (self.no_deliver or self.export_only):
            for alt_index in range(len(getattr(settings, "EMAIL_ALTERNATIVE", [])) + 1):
                self.smtp_servers.append(smtp_connect(alt_index))
            if not any(self.smtp_servers):
                # At least 1 smtp server must be available
                self.log.error("All MTA down, '%s %s' was used for partitions and mod" % (self.partitions, self.mod))
                return

        s_id, is_subscriber, nl_delivery_date = None, None, self.nl_delivery_dt.strftime("%Y%m%d")
        email_template = Engine.get_default().get_template(self.get_template_name())

        while True:

            try:
                if not self.retry_last_delivery:
                    if self.offline:
                        # TODO: check if this try is needed in the other "send NL" management commads
                        try:
                            s_next = next(subscribers_iter)
                            (
                                s_id,
                                s_name,
                                s_user_email,
                                s_contact_id,
                                hashed_id,
                                is_subscriber,
                                is_subscriber_any,
                                is_subscriber_default,
                            ) = s_next[:8]
                            s_extra = self.subscriber_extra(s_next[8:])
                        except ValueError:
                            raise CommandError(
                                "Unable to parse subscribers CSV file, a probabble reason can be it was generated "
                                "with an old version of this script"
                            )
                        else:
                            is_subscriber = eval(is_subscriber)
                            is_subscriber_any = eval(is_subscriber_any)
                            is_subscriber_default = eval(is_subscriber_default)
                    else:
                        s, is_subscriber = next(subscribers_iter)
                        s_id, s_name, s_user_email, s_contact_id = s.id, s.get_full_name(), s.user.email, s.contact_id
                        s_extra = self.subscriber_extra(s.extra_info)
                        hashed_id = hashids.encode(int(s_id))
                        is_subscriber_any = s.is_subscriber_any()
                        is_subscriber_default = s.is_subscriber(self.pub_slug)

                if self.export_subscribers:
                    export_subscribers_writer.writerow(
                        [
                            s_id,
                            s_name,
                            s_user_email,
                            s_contact_id,
                            hashed_id,
                            is_subscriber,
                            is_subscriber_any,
                            is_subscriber_default,
                        ] + [s_extra.get(key) for key in self.subscriber_extra_info_keys]
                    )
                elif not self.export_context:

                    if self.as_news:
                        unsubscribe_url = '%s/usuarios/perfil/disable/allow_news/%s/' % (site_url, hashed_id)
                    else:
                        unsubscribe_url = '%s/usuarios/nlunsubscribe/%s/%s/?utm_source=newsletter&utm_medium=email' \
                            '&utm_campaign=%s&utm_content=unsubscribe' % (
                                site_url, self.pub_slug, hashed_id, self.newsletter_campaign
                            )
                    browser_preview_url = '%s/nl/%s/%s/' % (site_url, self.pub_slug, hashed_id)
                    context.update(
                        {
                            'unsubscribe_url': unsubscribe_url,
                            'browser_preview_url': browser_preview_url,
                            'subscriber_id': s_id,
                            'is_subscriber': is_subscriber,
                            'is_subscriber_any': is_subscriber_any,
                            'is_subscriber_default': is_subscriber_default,
                            "track_open_event_url": "%s/usuarios/nl_track/%c_%s_%s_%s.gif" % (
                                site_url,
                                "s" if is_subscriber else "r",
                                hashed_id,
                                self.newsletter_campaign,
                                nl_delivery_date,
                            ),
                        }
                    )
                    if hasattr(self, 'download_allowed') and self.download_allowed(s_extra):
                        context["download_url"] = edition_download_url
                    headers = common_headers.copy()
                    headers['Message-Id'] = make_msgid(str(s_id))
                    headers['List-Unsubscribe'] = '<%s>' % unsubscribe_url
                    headers['List-Unsubscribe-Post'] = "List-Unsubscribe=One-Click"
                    msg = Message(
                        html=email_template.render(Context(context)),
                        mail_to=(s_name, s_user_email),
                        subject=email_subject,
                        mail_from=(email_from_name, settings.NOTIFICATIONS_FROM_ADDR1),
                        headers=headers,
                    )

                    # attach ads and others files if any
                    extra_attachments = []
                    if hasattr(self, 'extra_attachments'):
                        extra_attachments = self.extra_attachments(s_extra, edition_download_url)
                    for f_ad in (f_ads + extra_attachments):
                        self.msg_attach_file(msg, f_ad)

                    self.sendmail(s_user_email, self.log, msg, is_subscriber, s_id)
                    if not (self.no_deliver or any(self.smtp_servers)):
                        self.log.error(
                            "All MTA down, (%s, %s, %s, %s) was the last delivery attempt" % (
                                s_user_email if s_id else None, is_subscriber, self.partitions, self.mod
                            )
                        )
                        break

            except (ProgrammingError, OperationalError, StopIteration) as exc:
                # the connection to databse can be killed, if that is the case print useful log to continue
                if isinstance(exc, (ProgrammingError, OperationalError)):
                    self.log.error(
                        'DB connection error, (%s, %s, %s, %s) was the last delivery attempt' % (
                            s_user_email if s_id else None, is_subscriber, self.partitions, self.mod
                        )
                    )
                break

    def set_nlobj(self, ed_date):
        self.nlobj = DefaultNewsletter.objects.get(day=ed_date)

    def handle(self, *args, **options):
        self.pub_slug = options.get("publication_slug")
        if self.pub_slug in self.disallowed_publications:
            raise CommandError("The newsletter of this publication is not allowed to be sent using this command")

        self.load_options(options)
        ed_date = options.get('edition_date')

        if (self.offline or self.export_subscribers) and ed_date:
            raise CommandError('--edition-date can not be used with --offline or --export-subscribers')

        self.initlog(self.log, self.pub_slug)

        try:

            offline_edition_file = join(settings.SENDNEWSLETTER_EXPORT_DIR, self.pub_slug + '_edition.json')
            if self.offline:
                self.edition = json.loads(open(offline_edition_file).read())
                if (
                    not self.nlobj_pubs_edition_use_latest
                    and self.edition.get('date_published_iso') != self.nl_delivery_dt.strftime("%Y-%m-%d")
                ):
                    error_msg = "Serialized edition date does not match today's date"
                    self.log.error(error_msg)
                    raise CommandError(error_msg)
            elif not self.export_subscribers:
                editions = Edition.objects.filter(publication__slug=self.pub_slug)
                if self.pub_slug in self.nlobj_pubs:
                    ed_date_lookup = ed_date or make_naive(self.nl_delivery_dt).date()
                    try:
                        self.edition = editions.get(date_published=ed_date_lookup)
                    except Edition.DoesNotExist:
                        if not ed_date and self.nlobj_pubs_edition_use_latest:
                            self.edition = editions.latest()
                            ed_date_lookup = self.edition.date_published
                        else:
                            ed_date = ed_date_lookup
                            raise
                    try:
                        self.set_nlobj(ed_date_lookup)
                    except ObjectDoesNotExist:
                        pass
                else:
                    self.edition = editions.get(date_published=ed_date) if ed_date else editions.latest()
                if self.export_context:
                    open(offline_edition_file, 'w').write(json.dumps(self.edition.nl_serialize()))

            self.only_supplements, self.site_id = options.get('only_supplements'), options.get('site_id')

        except FileNotFoundError:
            error_msg = "Aborting, no '%s' edition serialized file found." % self.pub_slug
            self.log.error(error_msg)
            raise CommandError(error_msg)
        except Edition.DoesNotExist:
            error_msg = "Aborting, no '%s' edition found%s." % (self.pub_slug, (" on %s" % ed_date) if ed_date else "")
            self.log.error(error_msg)
            raise CommandError(error_msg)
        else:
            self.send_subscribers_mail()
            self.finish(self.log, getattr(self, "newsletter_campaign", None))
