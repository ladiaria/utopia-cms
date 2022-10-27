# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
from builtins import str
import requests
import json
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from requests.exceptions import ConnectionError
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.core.exceptions import MultipleObjectsReturned
from django.core.mail import send_mail
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect, HttpResponse, BadHeaderError, HttpResponsePermanentRedirect
from django.views.generic import DetailView
from django.contrib.sites.models import Site
from django.shortcuts import get_list_or_404, get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache, cache_page
from django.views.decorators.vary import vary_on_cookie
from django.template.defaultfilters import slugify

from actstream.models import following
from favit.models import Favorite

from tagging.models import Tag
from apps import mongo_db
from decorators import decorate_if_no_staff, decorate_if_staff
from core.forms import ReportErrorArticleForm, SendByEmailForm
from core.models import Publication, Category, Article, ArticleUrlHistory


standard_library.install_aliases()


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
    pubdate = date.today()
    if datetime.now().hour < 8:
        pubdate -= timedelta(days=1)
    articles = get_list_or_404(Article, is_published=True, type=atype['slug'], date_published__lte=pubdate)
    paginator = Paginator(articles, 10)
    try:
        page = request.GET.get('pagina', 1)
    except ValueError:
        page = 1
    try:
        articles = paginator.page(page)
    except (EmptyPage, InvalidPage):
        articles = paginator.page(paginator.num_pages)
    return render(request, 'section/detail.html', {'articles': articles, 'section': atype})


def article_detail(request, year, month, slug, domain_slug=None):
    domain, category = 'publication', None
    if domain_slug:
        try:
            Publication.objects.get(slug=domain_slug)
        except Publication.DoesNotExist:
            try:
                category = Category.objects.get(slug=domain_slug)
            except Category.DoesNotExist:
                if domain_slug not in getattr(settings, 'CORE_HISTORIC_DOMAIN_SLUGS', ()):
                    raise Http404
            else:
                domain = 'category'

    if settings.DEBUG:
        print('DEBUG: article_detail view called with (%d, %d, %s, %s)' % (year, month, slug, domain_slug))
    if settings.AMP_DEBUG and request.flavour == 'amp':
        print('AMP DEBUG: request.META=%s' % request.META)

    # 1. obtener articulo
    try:
        # netloc splitted by port (to support local environment running in port)
        netloc, first_of_month = request.META['HTTP_HOST'].split(':')[0], date(year, month, 1)
        first_of_month_plus1 = first_of_month + relativedelta(months=1)
        # when the article is not published, it has no date_published, then date_created should be used
        article = Article.objects.select_related('main_section__edition__publication').get(
            Q(is_published=True) & Q(date_published__gte=first_of_month)
            & Q(date_published__lt=first_of_month_plus1) | Q(is_published=False)
            & Q(date_created__gte=first_of_month) & Q(date_created__lt=first_of_month_plus1),
            slug=slug,
        )
        article_url = article.get_absolute_url()
        if request.path != article_url:
            s = urlsplit(request.get_full_path())
            return HttpResponsePermanentRedirect(
                urlunsplit((settings.URL_SCHEME, netloc, article_url, s.query, s.fragment))
            )
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
                return HttpResponsePermanentRedirect(
                    urlunsplit((settings.URL_SCHEME, netloc, last_by_hist_url, s.query, s.fragment))
                )
            else:
                # show "draft" only for staff users
                if request.user.is_staff:
                    article = last_by_hist.article
                else:
                    raise Http404
        else:
            raise Http404

    # 2. access to staff only if the article is not published
    if not article.is_published and not request.user.is_staff:
        raise Http404

    report_form = ReportErrorArticleForm(article=article)
    user_is_authenticated = request.user.is_authenticated()

    if request.method == 'POST':
        post = request.POST.copy()
        if 'error' in post and user_is_authenticated:
            report_form = ReportErrorArticleForm(post, article=article)
            if report_form.is_valid():
                return report_error(request, article)

    signupwall_exclude_request_condition = getattr(settings, 'SIGNUPWALL_EXCLUDE_REQUEST_CONDITION', lambda r: False)
    if settings.CORE_LOG_ARTICLE_VIEWS and not (
        signupwall_exclude_request_condition(request) or request.flavour == 'amp'
    ):
        if request.user.is_authenticated() and mongo_db is not None:
            # register this view
            set_values = {'viewed_at': datetime.now()}
            if getattr(request, 'article_allowed', False):
                set_values['allowed'] = True
            mongo_db.core_articleviewedby.update_one(
                {'user': request.user.id, 'article': article.id}, {'$set': set_values}, upsert=True
            )
        # inc this article visits
        if mongo_db is not None:
            mongo_db.core_articlevisits.update_one({'article': article.id}, {'$inc': {'views': 1}}, upsert=True)

    try:
        talk_url = getattr(settings, 'TALK_URL', None)
        if talk_url and article.allow_comments:
            talk_story = requests.post(
                talk_url + 'api/graphql',
                headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + settings.TALK_API_TOKEN},
                data='{"query":"query GetComments($id:ID!){story(id: $id){comments{nodes{status}}}}","variables":'
                '{"id":%d},"operationName":"GetComments"}' % article.id
            ).json()['data']['story']
            comments_count = len(talk_story['comments']['nodes']) if talk_story else 0
        else:
            comments_count = 0
    except (ConnectionError, ValueError, KeyError):
        comments_count = 0

    publication = article.main_section.edition.publication if article.main_section else None
    context = {
        'article': article,
        'is_detail': True,
        'report_form': report_form,
        'domain': domain,
        'category': category,
        'category_signup':
            domain == u'category' and category.slug in getattr(settings, 'CORE_CATEGORIES_CUSTOM_SIGNUP', ()),
        'section': article.publication_section(),
        'header_display': article.header_display,
        'tag_list': reorder_tag_list(article, get_article_tags(article)),
        'comments_count': comments_count,
        'publication': publication,
        'signupwall_enabled': settings.SIGNUPWALL_ENABLED,
        'publication_newsletters':
            Publication.objects.filter(has_newsletter=True).exclude(slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL),
        'date_published_use_main_publication': publication and publication.slug in getattr(
            settings, 'CORE_ARTICLE_DETAIL_DATE_PUBLISHED_USE_MAIN_PUBLICATIONS', ()),
    }

    if user_is_authenticated:
        context.update(
            {
                'followed': article in following(request.user, Article),
                'favourited': article in [f.target for f in Favorite.objects.for_user(request.user)],
            }
        )

    template = getattr(settings, 'CORE_ARTICLE_DETAIL_TEMPLATE', 'article/detail.html')
    if request.flavour == 'amp':
        template = getattr(settings, 'CORE_ARTICLE_DETAIL_TEMPLATE_AMP', template)
    return render(request, template, context)


@never_cache
def article_detail_walled(request, year, month, slug, domain_slug=None):
    return article_detail(request, int(year), int(month), slug, domain_slug)


@decorate_if_staff(decorator=never_cache)
@decorate_if_no_staff(decorator=vary_on_cookie)
@decorate_if_no_staff(decorator=cache_page(120))
def article_detail_free(request, year, month, slug, domain_slug=None):
    return article_detail(request, int(year), int(month), slug, domain_slug)


def reorder_tag_list(article, tags):
    """
    Reorder all Tag in tags in the same order that article.tags
    if there is a problem with the article.tags, returns the same list (ordered alphabetycally)
    """
    reordered_tags = []
    if not article.tags:
        return tags
    strip_tags = [
        tag.strip() for tag in article.tags.split(',') if tag.strip()]
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
    article_tags = Tag.objects.get_for_object(article)
    return article_tags


def report_error(request, article):
    from django.core.mail import mail_managers

    body = """Reporte enviado por %(name)s sobre el artículo "%(article)s":
    %(message)s

Puede editar el artículo en:
    https://%(site)s/admin/core/article/%(id)i/
    """ % {
        'name': request.user.get_full_name(),
        'article': article.headline,
        'message': request.POST.get('error'),
        'id': article.id,
        'site': Site.objects.get_current().domain,
    }
    mail_managers(subject='Error en artículo', message=body)
    return HttpResponseRedirect(reverse('article_report_sent'))


@require_http_methods(["POST"])
def send_by_email(request):
    form = SendByEmailForm(data=request.POST)
    if form.is_valid():
        email = form.data["email"]
        message = form.data["message"]
        article = Article.objects.get(pk=form.data["article_id"])
        if request.user.is_authenticated():
            user_name = request.user.get_full_name()
        else:
            user_name = u"Usuario anónimo"

        body = """%(name)s compartió contigo el artículo "%(article)s":
        %(message)s
Podés ver el artículo aquí: %(url)s
        """ % {'name': user_name, 'article': article.headline, 'message': message, 'url': article.get_absolute_url()}

        try:
            send_mail('Te recomiendan un artículo', body, settings.DEFAULT_FROM_EMAIL, [email])
            data = {"status": "OK", "email": email}
        except BadHeaderError:
            return HttpResponse('Cabezal incorrecto.')
    else:
        data = {"status": "ERROR", "errors": str(form.errors["email"])}
    return HttpResponse(json.dumps(data), content_type="application/json")
