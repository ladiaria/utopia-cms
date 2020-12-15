# -*- coding: utf-8 -*-
import socket
from datetime import datetime, timedelta
from hashids import Hashids

from decorators import render_response
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseServerError, HttpResponseForbidden, HttpResponsePermanentRedirect
from django.views.decorators.cache import never_cache
from django.template import RequestContext
from django.shortcuts import redirect, get_object_or_404, render_to_response
from django.core.urlresolvers import reverse

from core.models import Publication, Category, Section, Article, get_latest_edition
from home.models import Home
from faq.models import Question, Topic


to_response = render_response('core/templates/category/')

# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


@never_cache
def category_detail(request, slug):

    # deporte custom redirect
    if slug == u'deporte':
        return redirect(Publication.objects.get(slug=u'garra').get_absolute_url(), permanent=True)

    category, inner_sections = get_object_or_404(Category, slug=slug), []
    question_list, questions_topic = [], None
    category_home = get_object_or_404(Home, category=category)
    cat_modules = category_home.modules.all()
    top_articles = cat_modules[0].articles_as_list if cat_modules else []
    try:
        featured_section1 = category.section_set.get(home_order=1)
    except (Section.DoesNotExist, Section.MultipleObjectsReturned):
        featured_section1 = None
    try:
        featured_section2 = category.section_set.get(home_order=2)
    except (Section.DoesNotExist, Section.MultipleObjectsReturned):
        featured_section2 = None
    try:
        featured_section3 = category.section_set.get(home_order=3)
    except (Section.DoesNotExist, Section.MultipleObjectsReturned):
        featured_section3 = None

    # custom inner sections
    if slug == u'elecciones':
        # example dropdown menu (elecciones ir disabled now by redirect)
        inner_sections = category.section_set.filter(
            Q(slug__startswith='partido-') | Q(slug__in=(
                'frente-amplio', 'unidad-popular', 'cabildo-abierto', 'otros')))
    if slug == u'coronavirus':
        question_list = Question.published.filter(topic__slug='coronavirus')
        try:
            questions_topic = Topic.objects.get(slug="coronavirus")
        except Topic.DoesNotExist:
            pass

    return render_to_response(
        '%s/%s.html' % (
            getattr(settings, 'CORE_CATEGORIES_TEMPLATE_DIR', 'core/templates/category'),
            category.slug if category.slug in getattr(settings, 'CORE_CATEGORIES_CUSTOM_TEMPLATES', ()) else 'detail'
        ), {
            'category': category, 'cover_article': category_home.cover, 'destacados': top_articles, 'is_portada': True,
            'featured_section1': featured_section1, 'featured_section2': featured_section2,
            'featured_section3': featured_section3, 'inner_sections': inner_sections, 'edition': get_latest_edition(),
            'question_list': question_list, 'questions_topic': questions_topic,
            'big_photo': category.full_width_cover_image}, context_instance=RequestContext(request))


@never_cache
@to_response
def newsletter_preview(request, slug):

    # allow only staff members or requests from localhost
    if not (request.user.is_staff or request.META.get('REMOTE_ADDR') in (
            socket.gethostbyname('localhost'), socket.gethostbyname(socket.gethostname()))):
        return HttpResponseForbidden()

    # removed or changed categories redirects by settings
    if slug in getattr(settings, 'CORE_CATEGORY_REDIRECT', {}):
        return HttpResponsePermanentRedirect(
            reverse('category-nl-preview', args=(settings.CORE_CATEGORY_REDIRECT[slug], )))

    category = get_object_or_404(Category, slug=slug)
    category_home = get_object_or_404(Home, category=category)
    cat_modules = category_home.modules.all()

    try:
        cover_article = category_home.cover
        cover_article_section = cover_article.publication_section()
        top_articles = [
            (a, a.publication_section(), 0) for a in (cat_modules[0].articles_as_list if cat_modules else [])]

        opinion_article = None
        nl_featured = Article.objects.filter(id=settings.NEWSLETTER_FEATURED_ARTICLE) if \
            getattr(settings, 'NEWSLETTER_FEATURED_ARTICLE', False) else \
            get_latest_edition().newsletter_featured_articles()
        if nl_featured:
            opinion_article = nl_featured[0]

        # datos_article for elecciones
        try:
            datos_article = category.section_set.get(slug='datos-elecciones-2019').latest_article()[0]
        except (Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError):
            datos_article = None

        try:
            hashed_id = hashids.encode(int(request.user.subscriber.id))
        except AttributeError:
            hashed_id = hashids.encode(0)
        return 'newsletter/%s.html' % slug, {
            'cover_article': cover_article, 'category': category, 'cover_article_section': cover_article_section,
            'articles': top_articles, 'hashed_id': hashed_id, 'opinion_article': opinion_article,
            'site_url': '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN), 'datos_article':
                datos_article if
                datos_article and datos_article.date_published >= datetime.now() - timedelta(1) else None}
    except Exception as e:
        return HttpResponseServerError(u'ERROR: %s' % e)
