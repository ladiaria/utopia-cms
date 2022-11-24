# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import never_cache, cache_control
from django.urls.exceptions import NoReverseMatch
from django.contrib.contenttypes.models import ContentType

from decorators import decorate_if_no_staff, decorate_if_staff

from core.models import Edition, get_current_edition, Publication, Category, CategoryHome, Article
from core.views.category import category_detail
from faq.models import Question, Topic
from cartelera.models import LiveEmbedEvent


def ctx_update_article_extradata(context, user, user_has_subscriber, follow_set, articles):
    for a in articles:
        is_restricted, compute_follow = a.is_restricted(), False
        if is_restricted:
            context['restricteds'].append(a.id)
            if user_has_subscriber and user.subscriber.is_subscriber(a.main_section.edition.publication.slug):
                context['restricteds_allowed'].append(a.id)
                compute_follow = True
        else:
            compute_follow = True
        if compute_follow:
            context['compute_follows'].append(a.id)
            if str(a.id) in follow_set:
                context['follows'].append(a.id)


@decorate_if_staff(decorator=never_cache)
@decorate_if_no_staff(decorator=vary_on_cookie)
@decorate_if_no_staff(
    decorator=cache_control(
        no_cache=True, no_store=True, must_revalidate=True, max_age=getattr(settings, 'HOMEV3_INDEX_CACHE_MAXAGE', 120)
    )
)
def index(request, year=None, month=None, day=None, domain_slug=None):
    """
    View to display the current edition page. Or the edition in the date and publication matching domain_slug.
    If domain_slug is a Category slug this view will return the matching category detail view.
    """

    if domain_slug:
        # if domain_slug is one of the "root url" publications => redirect to home (only if no edition date given)
        if domain_slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL and not (year or month or day):
            return HttpResponsePermanentRedirect(reverse('home'))
        try:
            publication = Publication.objects.get(slug=domain_slug)
            # if not public => only allow staff members
            if not (publication.public or request.user.is_staff):
                raise Http404
        except Publication.DoesNotExist:
            # if domain_slug is an area slug (or a slug to redirect) => return area detail view
            category_redirections = getattr(settings, 'CORE_CATEGORY_REDIRECT', {})
            if domain_slug in category_redirections:
                # removed, changed or force-404 categories redirects by settings
                redirect_slug = category_redirections[domain_slug]
                if redirect_slug:
                    if redirect_slug.startswith('/'):
                        # support for a "direct path" temporal redirect
                        # TODO: the settings could include the temporal/permanent option
                        return redirect(redirect_slug)
                    try:
                        return HttpResponsePermanentRedirect(
                            reverse('home', args=(settings.CORE_CATEGORY_REDIRECT[domain_slug], ))
                        )
                    except NoReverseMatch:
                        raise Http404
                else:
                    raise Http404
            return category_detail(request, get_object_or_404(Category, slug=domain_slug).slug)
    else:
        publication = Publication.objects.get(slug=settings.DEFAULT_PUB)

    # Primer día desde el que se muestran ediciones.
    # TODO: explain better this setting
    first_day = getattr(settings, 'FIRST_DAY')

    edition = None
    publishing_hour, publishing_minute = [int(i) for i in settings.PUBLISHING_TIME.split(':')]

    # Context variables for publication, featured publications, sections "grids" and "big photo".
    context = {
        'publication': publication,
        'featured_publications': [],
        'featured_sections': getattr(settings, 'HOMEV3_FEATURED_SECTIONS', {}).get(publication.slug, ()),
        'bigphoto_template': getattr(settings, 'HOMEV3_BIGPHOTO_TEMPLATE', 'bigphoto.html'),
    }

    is_authenticated = request.user.is_authenticated()
    if is_authenticated:
        context.update({'restricteds': [], 'restricteds_allowed': [], 'compute_follows': [], 'follows': []})
        user_has_subscriber = hasattr(request.user, 'subscriber')
        follow_set = request.user.follow_set.filter(
            content_type=ContentType.objects.get_for_model(Article)
        ).values_list('object_id', flat=True)

    for publication_slug in getattr(settings, 'HOMEV3_FEATURED_PUBLICATIONS', ()):
        try:
            ftop_articles = \
                get_current_edition(publication=Publication.objects.get(slug=publication_slug)).top_articles
            if ftop_articles:
                if is_authenticated:
                    ctx_update_article_extradata(context, request.user, user_has_subscriber, follow_set, ftop_articles)
                fcover_article = ftop_articles[0]
                ftop_articles.pop(0)
            else:
                fcover_article = None
        except Publication.DoesNotExist:
            pass
        else:
            context['featured_publications'].append((publication_slug, ftop_articles, fcover_article))

    # Context variables for the featured category component
    featured_category_slug = getattr(settings, 'HOMEV3_FEATURED_CATEGORY', None)
    if featured_category_slug:
        category = get_object_or_404(Category, slug=featured_category_slug)
        category_home = get_object_or_404(CategoryHome, category=category)
        category_cover_article, category_destacados = category_home.cover(), category_home.non_cover_articles()
        if is_authenticated:
            ctx_update_article_extradata(
                context, request.user, user_has_subscriber, follow_set, [category_cover_article]
            )
            ctx_update_article_extradata(context, request.user, user_has_subscriber, follow_set, category_destacados)
        context.update(
            {
                'fcategory': category,
                'category_cover_article': category_cover_article,
                'category_destacados': category_destacados,
            }
        )

    questions_topic_slug = getattr(settings, 'HOMEV3_QUESTIONS_TOPIC_SLUG', None)
    if questions_topic_slug:
        question_list = Question.published.filter(topic__slug=questions_topic_slug)
        try:
            questions_topic = Topic.objects.get(slug=questions_topic_slug)
        except Topic.DoesNotExist:
            questions_topic = None
    else:
        question_list, questions_topic = [], None

    if publication.slug != settings.DEFAULT_PUB:
        if year and month and day:
            date_published = datetime(
                year=int(year), month=int(month), day=int(day), hour=publishing_hour, minute=publishing_minute)
            if first_day.date() > date_published.date():
                raise Http404
            if date_published >= datetime.now() and not request.user.is_staff:
                raise Http404
            edition = get_object_or_404(Edition, date_published=date_published, publication=publication)
        else:
            edition = get_current_edition(publication=publication)

        top_articles = edition.top_articles if edition else []

        context.update(
            {
                'edition': edition,
                'mas_leidos': False,
                'allow_ads': getattr(settings, 'HOMEV3_NON_DEFAULT_PUB_ALLOW_ADS', True),
            }
        )
        template = getattr(settings, 'HOMEV3_NON_DEFAULT_PUB_TEMPLATE', 'index_pubs.html')
    else:
        if year and month and day:
            date_published = datetime(
                year=int(year), month=int(month), day=int(day), hour=publishing_hour, minute=publishing_minute)
            if first_day.date() > date_published.date():
                raise Http404
            if date_published >= datetime.now() and not request.user.is_staff:
                raise Http404
            ld_edition = get_object_or_404(
                Edition, date_published=date_published, publication__slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL)
        else:
            # get edition as usual
            ld_edition = get_current_edition()

        top_articles = ld_edition.top_articles if ld_edition else []

        try:
            context['event'] = LiveEmbedEvent.objects.get(active=True, in_home=True)
        except LiveEmbedEvent.DoesNotExist:
            pass

        if settings.DEBUG:
            print(u'DEBUG: Default home page view called.')
        context.update(
            {
                'edition': ld_edition,
                'mas_leidos': True,
                'allow_ads': True,
                'publications': Publication.objects.filter(public=True),
                'home_publications': settings.HOME_PUBLICATIONS,
            }
        )
        template = 'index.html'

    if top_articles:

        if is_authenticated:
            ctx_update_article_extradata(context, request.user, user_has_subscriber, follow_set, top_articles)

        cover_article = top_articles[0]
        top_articles.pop(0)

    else:
        cover_article = None

    context.update(
        {
            'is_portada': True,
            'cover_article': cover_article,
            'destacados': top_articles,
            'question_list': question_list,
            'questions_topic': questions_topic,
            'big_photo': publication.full_width_cover_image,
        }
    )
    if publication.meta_description:
        context['site_description'] = publication.meta_description

    if publication.slug in getattr(settings, 'CORE_PUBLICATIONS_CUSTOM_TEMPLATES', ()):
        template_dir = getattr(settings, 'CORE_PUBLICATIONS_TEMPLATE_DIR', None)
        if template_dir:
            template = '%s/%s.html' % (template_dir, publication.slug)
    return render(request, template, context)
