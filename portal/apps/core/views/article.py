# -*- coding: utf-8 -*-
import time
import logging
from os.path import join
from future import standard_library
from builtins import str
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit
from pydoc import locate
import requests
from requests.exceptions import ConnectionError
import json
from dateutil.relativedelta import relativedelta
from actstream.models import following
from favit.models import Favorite
from tagging.models import Tag
from pydantic import BaseModel, Field

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.core.exceptions import MultipleObjectsReturned
from django.core.mail import send_mail
from django.db.models import Q
from django.http import Http404, HttpResponse, BadHeaderError, HttpResponsePermanentRedirect, HttpResponseForbidden
from django.views.generic import DetailView
from django.forms import ValidationError
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import get_list_or_404, get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache, cache_page
from django.views.decorators.vary import vary_on_cookie
from django.template.defaultfilters import slugify
from django.utils.timezone import timedelta, now, datetime, utc
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test

from apps import mongo_db
from core.utils import ia_use_group
from signupwall.middleware import signupwall_exclude, subscriber_access
from decorators import decorate_if_no_auth, decorate_if_auth
from thedaily import get_talk_url
from thedaily.templatetags.thedaily_tags import has_restricted_access
from ..forms import SendByEmailForm, feedback_allowed, feedback_form, feedback_handler
from ..models import Publication, Category, Article, ArticleUrlHistory, PerplexityAPISettings
from ..utils import get_app_template


logging.basicConfig(level=logging.INFO)

standard_library.install_aliases()


class ClienteException(Exception):
    pass


class ArticleDetailView(DetailView):
    model = Article


def get_type(type_slug):
    for type in Article.TYPE_CHOICES:
        if type_slug == slugify(type[1]):
            return type
    return (None, None)


@never_cache
def article_list(request, type_slug):
    atype = {}
    atype['slug'], atype['name'] = get_type(type_slug)
    if not atype['slug']:
        raise Http404
    nowval = now()
    pubdate = nowval.date()
    if nowval.hour < 8:
        pubdate -= timedelta(days=1)
    articles = get_list_or_404(Article, is_published=True, type=atype['slug'], date_published__lte=pubdate)
    paginator = Paginator(articles, 10)
    page = request.GET.get('pagina')
    try:
        articles = paginator.page(page)
    except PageNotAnInteger:
        articles = paginator.page(1)
    except (EmptyPage, InvalidPage):
        articles = paginator.page(paginator.num_pages)
    return render(request, 'section/detail.html', {'articles': articles, 'section': atype})


class DefaultArticleDetailView(ArticleDetailView):
    object = None
    domain = "publication"
    category = None
    context_object_name = 'article'
    arglist = ('year', 'month', 'slug', 'domain_slug')
    redirect = None

    def set_domain(self, domain_slug):
        if domain_slug:
            try:
                Publication.objects.get(slug=domain_slug)
            except Publication.DoesNotExist:
                try:
                    self.category = Category.objects.get(slug=domain_slug)
                except Category.DoesNotExist:
                    if domain_slug not in getattr(settings, 'CORE_HISTORIC_DOMAIN_SLUGS', ()):
                        raise Http404
                else:
                    self.domain = 'category'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        for k, v in zip(self.arglist, args):
            setattr(self, k, v)
        self.set_domain(self.domain_slug)
        self.object = self.get_object()

    def get(self, request, *args, **kwargs):
        if self.redirect:
            return HttpResponsePermanentRedirect(self.redirect)
        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if self.object:
            return self.object
        request, article = self.request, None
        year, month, slug, domain_slug = (getattr(self, k) for k in self.arglist)

        if settings.DEBUG:
            print(f'DEBUG: article_detail view called with ({year}, {month}, {slug}, {domain_slug})')
        if settings.AMP_DEBUG and getattr(request, "is_amp_detect", False):
            print(f'AMP DEBUG: request.META={request.META}')

        # 1. obtener articulo
        try:
            # netloc splitted by port (to support local environment running in port)
            netloc = request.headers['host'].split(':')[0]
            if year and month:
                first_of_month = datetime(year, month, 1, tzinfo=utc)
                dt_range = (first_of_month, first_of_month + relativedelta(months=1))
                # when the article is not published, it has no date_published, then date_created should be used
                article = Article.objects.select_related('main_section__edition__publication').get(
                    Q(is_published=True) & Q(date_published__range=dt_range)
                    | Q(is_published=False) & Q(date_created__range=dt_range),
                    slug=slug,
                )
            else:
                article = Article.objects.select_related('main_section__edition__publication').get(slug=slug)
            article_url = article.get_absolute_url()
            if request.path != article_url:
                s = urlsplit(request.get_full_path())
                self.redirect = urlunsplit((settings.URL_SCHEME, netloc, article_url, s.query, s.fragment))
        except MultipleObjectsReturned:
            # TODO: this multiple article situation should be notified
            msg = "Más de un artículo con el mismo slug en el mismo mes."
            if settings.DEBUG:
                print('DEBUG: core.views.article.article_detail: ' + msg)
            raise Http404(msg)
        except Article.DoesNotExist:
            s = urlsplit(request.get_full_path())
            last_by_hist = ArticleUrlHistory.objects.filter(absolute_url=request.path).last()
            # TODO: compute filter count and if > 1 the situation should be notified
            if last_by_hist:
                last_by_hist_url = last_by_hist.article.get_absolute_url()
                # do not redirect if destination is the same url of this request (avoid loop)
                if last_by_hist_url != request.path:
                    self.redirect = urlunsplit((settings.URL_SCHEME, netloc, last_by_hist_url, s.query, s.fragment))
                else:
                    # show "draft" only for staff users (TODO: message uuser to "take action?")
                    if settings.DEBUG:
                        debug_msg_part1 = (
                            'DEBUG: core.views.article.article_detail: last_by_hist == article.get_absolute_url(), not'
                            'redirecting to avoid loop.'
                        )
                    if request.user.is_staff:
                        article = last_by_hist.article
                        if settings.DEBUG:
                            print(f'{debug_msg_part1} Rendering draft article (user is staff).')
                    else:
                        if settings.DEBUG:
                            print(f'{debug_msg_part1} Raising 404 (user is not staff)')
                        raise Http404
            else:
                raise Http404

        # 2. if it was found, access to staff only if the article is not published
        if article and not article.is_published and not request.user.is_staff:
            raise Http404
        return article

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.redirect:
            return context
        request, article = self.request, self.object

        signupwall_exclude_request_condition = signupwall_exclude(self.request)
        # If the call to the condition with the request as argument returns True, the visit is not logged to mongodb.

        # 3. render "landing facebook" if fb browser detected and previous condition is not met
        if not signupwall_exclude_request_condition:
            """
            this code can be migrated to the middleware itself, this way you can use the same logic for all the views,
            not only for the article detail view, it will cover the use case of links clicked mostly on IG that is more
            often editors put non-article links there. middleware has already comments about this in
            "ref_core.views.article.py:153"
            """
            fb_browser_type = getattr(request, 'fb_browser_type', None)
            if fb_browser_type:
                self.template_name = get_app_template("article/landing_facebook.html")
                return {'browser_type': fb_browser_type}

        # 4. log article views
        is_amp_detect, user_is_authenticated = getattr(request, "is_amp_detect", False), request.user.is_authenticated
        if settings.CORE_LOG_ARTICLE_VIEWS and not (
            signupwall_exclude_request_condition or getattr(request, 'restricted_article', False) or is_amp_detect
        ):
            if user_is_authenticated and mongo_db is not None:
                # register this view
                set_values = {'viewed_at': now()}
                if getattr(request, 'article_allowed', False):
                    set_values['allowed'] = True
                mongo_db.core_articleviewedby.update_one(
                    {'user': request.user.id, 'article': article.id}, {'$set': set_values}, upsert=True
                )
            # inc this article visits
            if mongo_db is not None:
                mongo_db.core_articlevisits.update_one({'article': article.id}, {'$inc': {'views': 1}}, upsert=True)

        # render/handle feedback/feedback_sent, if any
        report_form, report_form_sent = None, False
        if feedback_allowed(request, article):
            if request.method == 'POST':
                report_form = feedback_form(request.POST, article=article)
                if report_form.is_valid(article):
                    try:
                        feedback_handler(request, article)
                    except ValidationError as ve:
                        report_form.add_error(None, ve)
                    else:
                        report_form_sent = True
            else:
                report_form = feedback_form(article=article, request=request)

        # comments count/widget
        try:
            talk_url = get_talk_url()
            if talk_url and article.allow_comments:
                talk_story = requests.post(
                    talk_url + 'api/graphql',
                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + settings.TALK_API_TOKEN},
                    data='{"query":"query GetComments($id:ID!){story(id: $id){comments{nodes{status}}}}","variables":'
                    '{"id":%d},"operationName":"GetComments"}' % article.id,
                ).json()['data']['story']
                comments_count = len(talk_story['comments']['nodes']) if talk_story else 0
            else:
                comments_count = 0
        except (ConnectionError, ValueError, KeyError):
            comments_count = 0

        publication = article.main_section.edition.publication if article.main_section else (
            Publication.default() if not Publication.multi() else None
        )
        context.update(
            {
                "DEBUG": settings.DEBUG,
                'article': article,
                "article_restricted_cf": article.is_restricted_consider_full(),
                "photo_render_allowed": article.photo_render_allowed(),
                'is_detail': True,
                'report_form': report_form,
                'report_form_sent': report_form_sent,
                'domain': self.domain,
                'category': self.category,
                'category_signup':
                    self.category
                    and self.domain == (
                        'category' and self.category.slug in getattr(settings, 'CORE_CATEGORIES_CUSTOM_SIGNUP', ())
                    ),
                'section': article.publication_section(),
                'header_display': article.header_display,
                'tag_list': reorder_tag_list(article, get_article_tags(article)),
                'comments_count': comments_count,
                'publication': publication,
                'signupwall_enabled': settings.SIGNUPWALL_ENABLED,
                "signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS,
                "signupwall_label_exclusive": settings.SIGNUPWALL_LABEL_EXCLUSIVE,
                'publication_newsletters': (
                    Publication
                    .objects.filter(has_newsletter=True)
                    .exclude(slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL)
                ),
                'date_published_use_main_publication': (
                    publication
                    and publication.slug in (
                        getattr(settings, 'CORE_ARTICLE_DETAIL_DATE_PUBLISHED_USE_MAIN_PUBLICATIONS', ())
                    )
                ),
                "enable_amp":
                    settings.CORE_ARTICLE_DETAIL_ENABLE_AMP and not article.extensions_have_invalid_amp_tags(),
                "audio_template": (
                    "article/audio"
                    + ("_subscribers_only" if settings.CORE_ARTICLE_DETAIL_AUDIO_TRANSCRIPT_ONLY_SUBSCRIBERS else "")
                    + ".html"
                )
            }
        )

        context.update(
            {
                'followed': article in following(request.user, Article),
                'favourited': article in [f.target for f in Favorite.objects.for_user(request.user)],
                "signupwall_remaining_banner": settings.SIGNUPWALL_REMAINING_BANNER_ENABLED,
                "restricted_access": has_restricted_access(request.user, article),
            } if user_is_authenticated else {"signupwall_remaining_banner": settings.SIGNUPWALL_ENABLED}
        )

        type_dirname = "article/detail"
        self.template_name = get_app_template(
            join(type_dirname, f"{article.type}.html") if article.type else f"{type_dirname}.html"
        )
        return context


def get_article_detail_view():
    custom_view = getattr(settings, 'CORE_ARTICLE_DETAIL_VIEW_CLASS', None)
    return (locate(custom_view) if custom_view else DefaultArticleDetailView).as_view()


@never_cache
def article_detail_walled(request, year, month, slug, domain_slug=None):
    return get_article_detail_view()(request, int(year), int(month), slug, domain_slug)


@never_cache
@login_required
def article_detail_ipfs(request, article_id):
    article = get_object_or_404(Article, id=article_id, ipfs_upload=True, ipfs_cid__isnull=False)
    try:
        assert subscriber_access(request.user.subscriber, article)
        r = requests.get('https://ipfs.io/ipfs/%s/' % article.ipfs_cid)
        r.raise_for_status()
    except AssertionError:
        return HttpResponseForbidden()
    else:
        return render(
            request,
            "core/templates/article/detail_ipfs.html",
            {"is_detail": True, "ipfs_content": '\n'.join(r.text.splitlines()[1:])},
        )


@decorate_if_auth(decorator=never_cache)
@decorate_if_no_auth(decorator=vary_on_cookie)
@decorate_if_no_auth(decorator=cache_page(120))
def article_detail_free(request, year, month, slug, domain_slug=None):
    return get_article_detail_view()(request, int(year), int(month), slug, domain_slug)


def reorder_tag_list(article, tags):
    """
    Reorder all Tag in tags in the same order that article.tags
    if there is a problem with the article.tags, returns the same list (ordered alphabetycally)
    """
    reordered_tags = []
    if not article.tags:
        return tags
    strip_tags = [tag.strip() for tag in article.tags.split(',') if tag.strip()]
    strip_tags = [tag.strip('\"') for tag in strip_tags]
    for s_tag in strip_tags:
        slug = slugify(s_tag)
        found = False
        for tag in tags:
            tag_slug = slugify(tag.name)
            if tag_slug == slug:
                reordered_tags.append(tag)
                found = True
                break
        if not found:
            # unexpected situation, a Tag is not found in article.tags
            # so I return the original list
            return tags
    if reordered_tags:
        return reordered_tags
    else:
        return tags


def get_article_tags(article):
    return Tag.objects.get_for_object(article)


@require_http_methods(["POST"])
def send_by_email(request):
    form = SendByEmailForm(data=request.POST)
    if form.is_valid():
        email = form.data["email"]
        message = form.data["message"]
        article = Article.objects.get(pk=form.data["article_id"])
        if request.user.is_authenticated:
            user_name = request.user.get_full_name()
        else:
            user_name = "Usuario anónimo"

        body = """%(name)s compartió contigo el artículo "%(article)s":
        %(message)s
Podés ver el artículo aquí: %(url)s
        """ % {
            'name': user_name,
            'article': article.headline,
            'message': message,
            'url': article.get_absolute_url(),
        }

        try:
            send_mail('Te recomiendan un artículo', body, settings.DEFAULT_FROM_EMAIL, [email])
            data = {"status": "OK", "email": email}
        except BadHeaderError:
            return HttpResponse('Cabezal incorrecto.')
    else:
        data = {"status": "ERROR", "errors": str(form.errors["email"])}
    return HttpResponse(json.dumps(data), content_type="application/json")


@never_cache
@csrf_protect
@login_required
@user_passes_test(ia_use_group)
def perplexity_ask(request):
    def extract_valid_json(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts and returns only the valid JSON part from a response object.

        This function assumes that the response has a structure where the valid JSON
        is included in the 'content' field of the first choice's message, after the
        closing "</think>" marker. Any markdown code fences (e.g. ```json) are stripped.

        Parameters:
            response (dict): The full API response object.

        Returns:
            dict: The parsed JSON object extracted from the content.

        Raises:
            ValueError: If no valid JSON can be parsed from the content.
        """
        # Navigate to the 'content' field; adjust if your structure differs.
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Find the index of the closing </think> tag.
        marker = "</think>"
        idx = content.rfind(marker)

        if idx == -1:
            # If marker not found, try parsing the entire content.
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError("No </think> marker found and content is not valid JSON") from e

        # Extract the substring after the marker.
        json_str = content[idx + len(marker):].strip()

        # Remove markdown code fence markers if present.
        if json_str.startswith("```json"):
            json_str = json_str[len("```json"):].strip()
        if json_str.startswith("```"):
            json_str = json_str[3:].strip()
        if json_str.endswith("```"):
            json_str = json_str[:-3].strip()

        try:
            parsed_json = json.loads(json_str)
            return parsed_json
        except json.JSONDecodeError as e:
            raise ValueError("Failed to parse valid JSON from response content") from e

    def built_schema():
        class PerplexityAnswerFormat(BaseModel):
            metatitles: List[str] = Field(..., min_items=3, max_items=3)
            copys: List[str] = Field(..., min_items=2, max_items=2)

        return PerplexityAnswerFormat.model_json_schema()

    if request.method == "POST":
        config = PerplexityAPISettings.get_solo()
        if config.activar_asistente is False:
            message = "Asistente IA desactivado."
            response = {"error": True, "message": message, "status": 400}
            logging.error(f"{message}")
            return JsonResponse(response)

        data = json.loads(request.body.decode("utf-8"))
        titulo = data.get("titulo", "")
        cuerpo = data.get("cuerpo", "")
        descripcion = data.get("descripcion", "")
        article_id = data.get("article_id", "")
        api_response = None

        try:
            fields = [
                ("titulo", titulo, "No se envio el titulo."),
                ("cuerpo", cuerpo, "No se envio el cuerpo."),
            ]

            for field_name, value, error_message in fields:
                if value == "":
                    raise ClienteException(error_message)

            article = None
            if article_id != "":
                article = Article.objects.filter(id=article_id).first()
                if article is not None:
                    if article.ia_used:
                        raise ClienteException("No puede usarse la IA mas de una vez.")
                else:
                    raise Exception("El articulo no existe.")

            api_key = getattr(settings, "PERPLEXITY_API_KEY", None)
            if not api_key:
                raise Exception("API key de Perplexity no configurada.")

            url = config.endpoint
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            # Concatenate the default context and the question
            default_context = config.default_context.strip()

            if descripcion == "":
                # The description is not mandatory, and if it is not sent, then it is not sent to Perplexity.
                default_context = default_context.replace("Descripción: {descripcion}", "")
            else:
                default_context += default_context.replace("{descripcion}", descripcion)

            full_prompt = default_context.replace("{titulo}", titulo).replace("{cuerpo}", cuerpo)

            full_prompt += f" \n{config.result_instructions}"

            schema = built_schema()

            logging.info(f"pydentic schema: {schema}")

            payload = {
                "model": config.model,
                "messages": [
                    {"role": "system", "content": "Responde de manera clara y concisa."},
                    {"role": "user", "content": full_prompt},
                ],
                "search_domain_filter": config.get_domain_list(),
                "web_search_options": {"search_context_size": config.context_size},
                "response_format": {"type": "json_schema", "json_schema": {"schema": schema}},
            }

            search_domain_filter = config.get_domain_list()
            if len(search_domain_filter) > 0:
                payload["search_domain_filter"] = search_domain_filter

            # Solo incluye max_tokens si está definido en la configuración
            if config.temperature:
                payload["temperature"] = config.temperature
            if config.max_tokens:
                payload["max_tokens"] = config.max_tokens
            elif settings.DEBUG:
                payload["max_tokens"] = 100

            logging.info(f"calling the api with this data: {payload}")
            start_time = time.time()
            api_response = requests.post(url, headers=headers, json=payload, timeout=30)
            elapsed = time.time() - start_time
            logging.info(f"Tiempo de respuesta de Perplexity API: {elapsed:.2f} segundos")

            api_response.raise_for_status()
            data = extract_valid_json(api_response.json())

            if article is not None:
                article.ia_used = True
                article.save()

            response = {"error": False, "message": data}

        except ClienteException as ex:
            response = {"error": True, "message": str(ex), "status": 400}
            logging.error(f"Unexpected Error: {ex}", exc_info=True)
        except Exception as ex:
            answer = "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo más tarde."
            logging.error(f"Unexpected Error: {ex}", exc_info=True)
            response = {"error": True, "message": answer, "status": 500}
            if api_response is not None:
                answer = api_response.json()["error"]["message"]
                logging.error(f"API Respuesta: {answer}")
                response = {"error": True, "message": answer, "status": 500}
        return JsonResponse(response)
    return JsonResponse({"error": True, "message": "Método no permitido."}, status=405)
