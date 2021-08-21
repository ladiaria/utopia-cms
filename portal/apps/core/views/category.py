# -*- coding: utf-8 -*-
import sys
import socket
from datetime import datetime, timedelta
import traceback
from hashids import Hashids

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseServerError, HttpResponseForbidden, HttpResponsePermanentRedirect
from django.views.decorators.cache import never_cache
from django.template import RequestContext
from django.shortcuts import redirect, get_object_or_404, render
from django.core.urlresolvers import reverse

from core.models import Publication, Category, CategoryHome, Section, Article, get_latest_edition
from faq.models import Question, Topic


# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


@never_cache
def category_detail(request, slug):

    # deporte custom redirect
    if slug == u'deporte':
        return redirect(Publication.objects.get(slug=u'garra').get_absolute_url(), permanent=True)

    category, inner_sections = get_object_or_404(Category, slug=slug), []
    question_list, questions_topic = [], None
    category_home = get_object_or_404(CategoryHome, category=category)
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
            Q(slug__startswith='partido-') |
            Q(slug__in=('frente-amplio', 'unidad-popular', 'cabildo-abierto', 'otros'))
        )
    if slug == u'coronavirus':
        question_list = Question.published.filter(topic__slug='coronavirus')
        try:
            questions_topic = Topic.objects.get(slug="coronavirus")
        except Topic.DoesNotExist:
            pass

    return render(
        request,
        '%s/%s.html' % (
            getattr(settings, 'CORE_CATEGORIES_TEMPLATE_DIR', 'core/templates/category'),
            category.slug if category.slug in getattr(settings, 'CORE_CATEGORIES_CUSTOM_TEMPLATES', ()) else 'detail'
        ),
        {
            'category': category,
            'cover_article': category_home.cover(),
            'destacados': category_home.non_cover_articles(),
            'is_portada': True,
            'featured_section1': featured_section1,
            'featured_section2': featured_section2,
            'featured_section3': featured_section3,
            'inner_sections': inner_sections,
            'edition': get_latest_edition(),
            'question_list': question_list,
            'questions_topic': questions_topic,
            'big_photo': category.full_width_cover_image,
        },
    )


@never_cache
def newsletter_preview(request, slug):

    # allow only staff members or requests from localhost
    if not (request.user.is_staff or request.META.get('REMOTE_ADDR') in (
            socket.gethostbyname('localhost'), socket.gethostbyname(socket.gethostname()))):
        return HttpResponseForbidden()

    # removed or changed categories redirects by settings
    category_redirections = getattr(settings, 'CORE_CATEGORY_REDIRECT', {})
    if slug in category_redirections:
        redirect_slug = category_redirections[slug]
        if redirect_slug:
            return HttpResponsePermanentRedirect(
                reverse('category-nl-preview', args=(settings.CORE_CATEGORY_REDIRECT[slug], ))
            )

    category = get_object_or_404(Category, slug=slug)
    category_home = get_object_or_404(CategoryHome, category=category)

    try:
        cover_article = category_home.cover()
        cover_article_section = cover_article.publication_section() if cover_article else None
        top_articles = [(a, a.publication_section()) for a in category_home.non_cover_articles()]

        listonly_section = getattr(settings, 'CORE_CATEGORY_NEWSLETTER_LISTONLY_SECTIONS', {}).get(category.slug)
        if listonly_section:
            top_articles = [t for t in top_articles if t[1].slug == listonly_section]
            if cover_article_section.slug != listonly_section:
                cover_article = top_articles.pop(0)[0] if top_articles else None
                cover_article_section = cover_article.publication_section() if cover_article else None

        opinion_article = None
        nl_featured = Article.objects.filter(id=settings.NEWSLETTER_FEATURED_ARTICLE) if \
            getattr(settings, 'NEWSLETTER_FEATURED_ARTICLE', False) else \
            get_latest_edition().newsletter_featured_articles()
        if nl_featured:
            opinion_article = nl_featured[0]

        # featured_article (a featured section in the category)
        try:
            featured_section, days_ago = settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS[category.slug]
            featured_article = category.section_set.get(slug=featured_section).latest_article()[0]
            assert (featured_article.date_published >= datetime.now() - timedelta(days_ago))
        except (KeyError, Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError, AssertionError):
            featured_article = None

        try:
            hashed_id = hashids.encode(int(request.user.subscriber.id))
        except AttributeError:
            hashed_id = hashids.encode(0)

        site_url = '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN)
        unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
            '&utm_campaign=%s&utm_content=unsubscribe' % (site_url, category.slug, hashed_id, category.slug)

        return render(
            request,
            '%s/newsletter/%s.html' % (settings.CORE_CATEGORIES_TEMPLATE_DIR, slug),
            {
                'site_url': site_url,
                'category': category,
                'featured_article': featured_article,
                'opinion_article': opinion_article,
                'cover_article': cover_article,
                'cover_article_section': cover_article_section,
                'articles': top_articles,
                'newsletter_campaign': category.slug,
                'hashed_id': hashed_id,
                'unsubscribe_url': unsubscribe_url,
            },
        )

    except Exception as e:
        if settings.DEBUG:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(exc_type)
            print(exc_value)
            print(traceback.extract_tb(exc_traceback))
        return HttpResponseServerError(u'ERROR: %s' % e)
