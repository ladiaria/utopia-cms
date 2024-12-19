import socket
from os.path import join
from hashids import Hashids
from favit.utils import is_xhr

from django.conf import settings
from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.template import Engine
from django.template.exceptions import TemplateDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now
from django.db.utils import ProgrammingError
from django.contrib.sites.models import Site

from core.models import Publication, Edition, ArticleRel, DefaultNewsletter, get_latest_edition
from core.templatetags.ldml import remove_markup
from ..utils import serialize_wrapper

try:
    site = Site.objects.get_current()
except (ProgrammingError, Site.DoesNotExist):
    site = None

# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


def nl_template_name(publication_slug, default="newsletter/newsletter.html"):
    if publication_slug:
        template_dirs = [getattr(settings, "CORE_PUBLICATIONS_NL_TEMPLATE_DIR", "newsletter/publication")]
        if template_dirs[0]:
            template_dirs.append("")
        engine = Engine.get_default()
        for base_dir in template_dirs:
            template_try = join(base_dir, '%s.html' % publication_slug)
            try:
                engine.get_template(template_try)
                return template_try
            except TemplateDoesNotExist:
                pass
    return default


class NewsletterPreview(TemplateView):
    def get_template_name(self, *args, **kwargs):
        return nl_template_name(kwargs.get('publication_slug'))

    def get_defaults(self, publication_slug, day):
        default, default_nl = publication_slug == settings.DEFAULT_PUB, None
        if default:
            try:
                default_nl = DefaultNewsletter.objects.get(day=day)
            except DefaultNewsletter.DoesNotExist:
                pass
        return default, default_nl

    def dispatch(self, request, publication_slug):
        # allow only staff members or requests from localhost
        if not (
            request.user.is_staff
            or request.META.get('REMOTE_ADDR') in (
                socket.gethostbyname('localhost'), socket.gethostbyname(socket.gethostname())
            )
        ):
            raise PermissionDenied
        publication = get_object_or_404(Publication, slug=publication_slug)
        context = publication.extra_context.copy()
        context.update({"publication": publication, "preview_warn": ""})
        render_kwargs = {"context": context}
        template_name, template_name_default = None, self.template_name
        try:
            edition = get_latest_edition(publication)
        except Edition.DoesNotExist as edne:
            context.update({"headers_preview": True, "preview_err": edne})
            template_name = "newsletter/error.html"
            render_kwargs["status"] = 406
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
                        template_name = "newsletter/error.html"
                        render_kwargs["status"] = 406
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

                    if site and default:
                        email_from_name = site.name
                    elif publication.slug in getattr(settings, 'CORE_PUBLICATIONS_NL_FROM_NAME_NAMEONLY', ()):
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
                        email_subject = custom_subject_prefix + remove_markup(cover_article.headline)

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
                        template_name = "newsletter/error.html"
                        render_kwargs["status"] = 406
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
                template_name = "newsletter/error.html"
                render_kwargs["status"] = 406

        try:
            return render(request, template_name or template_name_default, **render_kwargs)
        except TemplateDoesNotExist:
            return render(request, template_name_default, **render_kwargs)
