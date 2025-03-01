import socket
from os.path import join
import json
from hashids import Hashids
from favit.utils import is_xhr

from django.conf import settings
from django.core.management import CommandError, call_command
from django.core.exceptions import PermissionDenied
from django.db.utils import ProgrammingError
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseBadRequest
from django.views.generic import TemplateView
from django.views.decorators.cache import never_cache
from django.template.exceptions import TemplateDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now, datetime
from django.utils.decorators import method_decorator
from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required

from libs.utils import decode_hashid
from thedaily.models import Subscriber
from ..models import Publication, Edition, ArticleRel, DefaultNewsletter, get_latest_edition
from ..templatetags.ldml import remove_markup
from ..utils import serialize_wrapper, nl_template_name


try:
    site = Site.objects.get_current()
except (ProgrammingError, Site.DoesNotExist):
    site = None


# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


@method_decorator(never_cache, name='dispatch')
class NewsletterPreview(TemplateView):
    delivery_command = "send_publication_nl"

    def get_template_name(self, *args, **kwargs):
        return nl_template_name(kwargs.get('publication_slug'))

    def get_default_nl(self, day):
        try:
            return DefaultNewsletter.objects.get(day=day)
        except DefaultNewsletter.DoesNotExist:
            return None

    def get_defaults(self, publication_slug, day):
        default = publication_slug == settings.DEFAULT_PUB
        default_nl = self.get_default_nl(day) if default else None
        return default, default_nl

    def authorize(self, request):
        # allow only staff members or requests from localhost
        if not (
            request.user.is_staff
            or request.META.get('REMOTE_ADDR') in (
                socket.gethostbyname('localhost'), socket.gethostbyname(socket.gethostname())
            )
        ):
            raise PermissionDenied

    def get(self, request, *args, **kwargs):
        self.authorize(request)
        publication_slug = kwargs.get('publication_slug')
        publication = get_object_or_404(Publication, slug=publication_slug)
        context = super().get_context_data()
        context.update({"newsletter_header_color": publication.newsletter_header_color, "preview_warn": ""})
        context.update(publication.extra_context.copy())
        status, template_name, template_name_default = None, None, self.template_name
        try:
            edition = get_latest_edition(publication)
        except Edition.DoesNotExist as edne:
            context.update({"headers_preview": True, "preview_err": edne})
            template_name, status = "newsletter/error.html", 406
        else:
            default, default_nl = self.get_defaults(publication.slug, edition.date_published)
            if default_nl:
                top_articles = default_nl.get_article_set().filter(article__is_published=True)
            else:
                top_articles = edition.top_articles
            if top_articles:
                # include sections (and include_photo flag)
                top_articles = [(a.article, a.include_photo) if default_nl else (a, False) for a in top_articles]

                # cover article (as in send_publication_nl command usage)
                cover_article = None
                if default:
                    err_msg = ''
                    try:
                        cover_article = (
                            default_nl.cover() if default_nl
                            else edition.articlerel_set.get(
                                article__is_published=True, home_top=True, top_position=1
                            ).article
                        )
                    except ArticleRel.DoesNotExist:
                        err_msg = 'Artículo de portada no configurado.'
                    except ArticleRel.MultipleObjectsReturned:
                        err_msg = 'Más de un artículo configurado como portada.'
                    if err_msg:
                        context.update({"headers_preview": True, "preview_err": err_msg})
                        template_name, status = "newsletter/error.html", 406
                else:
                    cover_article = top_articles.pop(0)[0]

                if cover_article:
                    try:
                        hashed_id = hashids.encode(int(request.user.subscriber.id))
                    except AttributeError:
                        hashed_id = hashids.encode(0)

                    # get logo url from publication's images or default to logo-white
                    logo_url = getattr(
                        publication.newsletter_logo or publication.image, 'url', '/static/img/logo-white.png'
                    )

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

                    custom_subject = \
                        publication.newsletter_automatic_subject is False and publication.newsletter_subject
                    if custom_subject:
                        email_subject = custom_subject
                    else:
                        custom_subject_prefix = \
                            self.custom_subject_prefix() if hasattr(self, 'custom_subject_prefix') else ""
                        email_subject = custom_subject_prefix + remove_markup(cover_article.nl_title)

                    headers = {
                        'From': '%s <%s>' % (email_from_name, settings.NOTIFICATIONS_FROM_ADDR1),
                        'Subject': email_subject,
                    }

                    site_url = settings.SITE_URL_SD
                    as_news = request.GET.get("as_news", "0").lower() in ("true", "1")
                    if as_news:
                        unsubscribe_url = '%s/usuarios/perfil/disable/allow_news/%s/' % (site_url, hashed_id)
                    else:
                        unsubscribe_url = '%s/usuarios/nlunsubscribe/%s/%s/?utm_source=newsletter&utm_medium=email' \
                            '&utm_campaign=%s&utm_content=unsubscribe' % (
                                site_url, publication_slug, hashed_id, publication.newsletter_campaign
                            )
                    headers['List-Unsubscribe'] = '<%s>' % unsubscribe_url
                    headers['List-Unsubscribe-Post'] = "List-Unsubscribe=One-Click"

                    try:
                        download_url = (
                            publication_slug in getattr(settings, 'CORE_PUBLICATIONS_EDITION_DOWNLOAD', [])
                            and edition.get_download_url()
                        )
                    except ValueError:
                        context.update({"headers_preview": True, "preview_err": "No hay PDF asociado a la edición"})
                        template_name, status = "newsletter/error.html", 406
                    else:
                        context.update(
                            {
                                'cover_article': serialize_wrapper(cover_article, publication, True, False),
                                'articles': serialize_wrapper(top_articles, publication, dates=False),
                                'hashed_id': hashed_id,
                                "as_news": as_news,
                                'unsubscribe_url': unsubscribe_url,
                                'site_url': site_url,
                                'logo_url': logo_url,
                                'download_url':
                                    request.GET.get("s_pdf", "0").lower() in ("true", "1") and download_url,
                                'newsletter_campaign': publication.newsletter_campaign,
                                'custom_subject': custom_subject,
                                'headers_preview': headers,
                                "request_is_xhr": is_xhr(request),
                                'nl_date': edition.date_published_verbose(False),
                            }
                        )

                        if default:

                            if edition.date_published != now().date():
                                if context["preview_warn"]:
                                    context["preview_warn"] += "<br>"
                                context["preview_warn"] += "La fecha de esta edición es distinta a la fecha de hoy"

                        # override is_subscriber_any and _default only to "False"
                        for suffix in ('any', 'default'):
                            is_subscriber_var = 'is_subscriber_' + suffix
                            is_subscriber_val = request.GET.get(is_subscriber_var)
                            if is_subscriber_val and is_subscriber_val.lower() in ('false', '0'):
                                context[is_subscriber_var] = False

                        template_name = self.get_template_name(publication_slug=publication_slug)

            else:
                context.update({"headers_preview": True, "preview_err": "Edición sin artículos de portada"})
                template_name, status = "newsletter/error.html", 406

        context.update(self.get_context_data())
        render_kwargs = {"context": context}
        if status:
            render_kwargs["status"] = status
        try:
            return render(request, template_name or template_name_default, **render_kwargs)
        except TemplateDoesNotExist:
            return render(request, template_name_default, **render_kwargs)

    def post(self, request, *args, **kwargs):
        """
        A post requests tries to send the newsletter to the user who's watching the preview.
        """
        self.authorize(request)
        u, publication_slug = request.user, kwargs.get('publication_slug')
        if publication_slug and u.email and hasattr(u, 'subscriber') and u.subscriber:
            cmd_args = [u.subscriber.id]
            cmd_opts = {
                "publication": publication_slug,
                "no_logfile": True,
                "no_update_stats": True,
                "force_no_subscriber": request.POST.get(f'is_subscriber_{publication_slug}') != "on",
                "assert_one_email_sent": True,
            }
            try:
                call_command(self.delivery_command, *cmd_args, **cmd_opts)
            except CommandError as cmde:
                return HttpResponseBadRequest(cmde)
        return HttpResponse()


@method_decorator(never_cache, name='dispatch')
class NewsletterBrowserPreview(TemplateView):
    def is_subscriber(self, subscriber, publication_slug):
        return subscriber.is_subscriber(publication_slug)

    def download_allowed(self, subscriber, publication_slug):
        return False

    def dispatch(self, request, publication_slug, hashed_id=None):
        if hashed_id:
            decoded = decode_hashid(hashed_id)
            # TODO: if authenticated => assert same logged in user
            if decoded:
                subscriber = get_object_or_404(Subscriber, id=decoded[0])
                if not subscriber.user:
                    raise Http404
            else:
                raise Http404
        else:
            # called from the auth view wrapper
            try:
                subscriber = request.user.subscriber
            except AttributeError:
                return HttpResponseForbidden()
        try:
            edition = json.loads(
                open(join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_edition.json' % publication_slug)).read()
            )
            context = json.loads(
                open(join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_ctx.json' % publication_slug)).read()
            )
        except IOError:
            raise Http404

        site_url, publication = context['site_url'], edition['publication']
        newsletter_campaign = publication['newsletter_campaign']
        context.update(
            {
                "browser_preview": True,
                'newsletter_campaign': newsletter_campaign,
                'newsletter_name': publication['newsletter_name'],
                'publication_name': publication['name'],
                'nl_date': edition['date_published'],
            }
        )
        # de-serialize dates
        dp_cover = datetime.strptime(context['cover_article']['date_published'], '%Y-%m-%d').date()
        context['cover_article']['date_published'] = dp_cover
        dp_articles, pub_is_default = [], publication_slug == settings.DEFAULT_PUB
        try:
            # TODO: check if this try is needed in the other browser preview views.
            for a, include_photo in context['articles']:
                dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
                a['date_published'] = dp_article
                dp_articles.append((a, include_photo))
        except ValueError:
            # TODO: mail managers
            context["preview_err"] = "Previsualización no disponible"

        as_news = request.GET.get("as_news", "0").lower() in ("true", "1")

        if hashed_id:
            if as_news:
                unsubscribe_url = '%s/usuarios/perfil/disable/allow_news/%s/' % (site_url, hashed_id)
            else:
                unsubscribe_url = '%s/usuarios/nlunsubscribe/%s/%s/?utm_source=newsletter&utm_medium=email' \
                    '&utm_campaign=%s&utm_content=unsubscribe' % (
                        site_url, publication_slug, hashed_id, newsletter_campaign
                    )
            context.update(
                {
                    'unsubscribe_url': unsubscribe_url,
                    "download_url":
                        self.download_allowed(subscriber, publication_slug) and edition.get('download_url'),
                }
            )

        context.update(
            {
                "articles": dp_articles,
                "as_news": as_news,
                "hashed_id": hashed_id,
                'subscriber_id': subscriber.id,
                'is_subscriber':
                    subscriber.is_subscriber() if pub_is_default else self.is_subscriber(subscriber, publication_slug),
                'is_subscriber_any': subscriber.is_subscriber_any(),
                'is_subscriber_default': subscriber.is_subscriber(settings.DEFAULT_PUB),
            }
        )

        return render(request, nl_template_name(publication_slug), context)


@never_cache
@login_required
def nl_browser_authpreview(request, slug):
    """
    wrapper view for the special url pattern for authenticated users
    """
    return NewsletterBrowserPreview.as_view()(request, slug)
