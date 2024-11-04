# -*- coding: utf-8 -*-

from datetime import datetime, date

from django_user_agents.utils import get_user_agent

from django.conf import settings
from django.urls import reverse
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_control, never_cache
from django.urls.exceptions import NoReverseMatch
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from decorators import decorate_if_no_auth, decorate_if_auth

from apps import bouncer_blocklisted
from core.models import Edition, get_current_edition, Publication, Category, CategoryHome, Article
from core.views.category import category_detail
from faq.models import Topic
from cartelera.models import LiveEmbedEvent
from thedaily.utils import unsubscribed_newsletters


cache_maxage = getattr(settings, 'HOMEV3_INDEX_CACHE_MAXAGE', 120)
decorate_auth = getattr(settings, 'HOMEV3_INDEX_AUTH_DECORATOR', decorate_if_auth)


def ctx_update_article_extradata(context, user, user_has_subscriber, follow_set, articles):
    for a in articles:
        compute_follow, a_id = True, a.id
        if a.is_restricted(True):
            context['restricteds'].append(a_id)
            compute_follow = (
                user_has_subscriber and user.subscriber.is_subscriber(a.main_section.edition.publication.slug)
            )
            if compute_follow:
                context['restricteds_allowed'].append(a_id)

        if compute_follow:
            context['compute_follows'].append(a_id)
            if str(a_id) in follow_set:
                context['follows'].append(a_id)


@decorate_auth(decorator=never_cache)
@decorate_if_no_auth(decorator=vary_on_cookie)
@decorate_if_no_auth(decorator=cache_control(no_cache=True, no_store=True, must_revalidate=True, max_age=cache_maxage))
def index(request, year=None, month=None, day=None, domain_slug=None):
    """
    View to display the current edition page. Or the edition in the date and publication matching domain_slug.
    If domain_slug is a Category slug this view will return the matching category detail view.
    """
    user = request.user
    if domain_slug:
        # if domain_slug is one of the "root url" publications => redirect to home (only if no edition date given)
        if domain_slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL and not (year or month or day):
            return HttpResponsePermanentRedirect(reverse('home'))
        try:
            publication = Publication.objects.get(slug=domain_slug)
            # if not public => only allow staff members
            if not (publication.public or user.is_staff):
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
                            reverse('home', args=(settings.CORE_CATEGORY_REDIRECT[domain_slug],))
                        )
                    except NoReverseMatch:
                        raise Http404
                else:
                    raise Http404
            return category_detail(request, get_object_or_404(Category, slug=domain_slug).slug)
    else:
        publication = Publication.objects.get(slug=settings.DEFAULT_PUB)

    edition = None
    publishing_hour, publishing_minute = [int(i) for i in settings.PUBLISHING_TIME.split(':')]

    # Context variables for publication, featured publications, sections "grids" and "big photo".
    context = publication.extra_context.copy()
    context.update(
        {
            "cache_maxage": cache_maxage,
            'publication': publication,
            'featured_publications': [],
            'featured_sections': getattr(settings, 'HOMEV3_FEATURED_SECTIONS', {}).get(publication.slug, ()),
            'news_wall_enabled': getattr(settings, 'HOMEV3_NEWS_WALL_ENABLED', True),
            'bigphoto_template': getattr(settings, 'HOMEV3_BIGPHOTO_TEMPLATE', 'bigphoto.html'),
            'allow_mas_leidos': getattr(settings, 'HOMEV3_ALLOW_MAS_LEIDOS', True),
        }
    )

    is_authenticated, user_has_subscriber = user.is_authenticated, hasattr(user, 'subscriber')
    if is_authenticated:
        context.update({'restricteds': [], 'restricteds_allowed': [], 'compute_follows': [], 'follows': []})
        follow_set = user.follow_set.filter(
            content_type=ContentType.objects.get_for_model(Article)
        ).values_list('object_id', flat=True)

    for pub_item in getattr(settings, 'HOMEV3_FEATURED_PUBLICATIONS', ()):
        pub_item_is_tuple = isinstance(pub_item, tuple)
        try:
            pub = Publication.objects.get(slug=pub_item[0] if pub_item_is_tuple else pub_item)
        except Publication.DoesNotExist:
            continue
        featured_section_slug = pub_item[1] if pub_item_is_tuple and len(pub_item) > 1 else None
        ftop_articles = get_current_edition(publication=pub).top_articles
        if ftop_articles:
            if is_authenticated:
                ctx_update_article_extradata(context, user, user_has_subscriber, follow_set, ftop_articles)
            fcover_article = ftop_articles[0]
            ftop_articles.pop(0)
            context['featured_publications'].append((pub, ftop_articles, fcover_article, featured_section_slug))

    # Context variables for the featured category component
    featured_category_slug = getattr(settings, 'HOMEV3_FEATURED_CATEGORY', None)
    if featured_category_slug:
        category = get_object_or_404(Category, slug=featured_category_slug)
        category_home = get_object_or_404(CategoryHome, category=category)
        category_cover_article, category_destacados = category_home.cover(), category_home.non_cover_articles()
        if is_authenticated:
            ctx_update_article_extradata(
                context, user, user_has_subscriber, follow_set, [category_cover_article] + list(category_destacados)
            )
        context.update(
            {
                'fcategory': category,
                'category_cover_article': category_cover_article,
                'category_destacados': category_destacados,
            }
        )

    questions_topic_slug, questions_topic = getattr(settings, 'HOMEV3_QUESTIONS_TOPIC_SLUG', None), None
    if questions_topic_slug:
        try:
            questions_topic = Topic.published.get(slug=questions_topic_slug)
        except Topic.DoesNotExist:
            pass

    if year and month and day:
        # case when a particular edition by date is requested
        date_published = timezone.make_aware(
            datetime(year=int(year), month=int(month), day=int(day), hour=publishing_hour, minute=publishing_minute)
        )
        # Optionally a custom setting can determine whether editions older than it are available.
        oldest_allowed = getattr(settings, "HOMEV3_EDITION_BY_DATE_OLDEST_ALLOWED", None)
        if (
            isinstance(oldest_allowed, date) and date_published.date() < oldest_allowed
            or date_published >= timezone.now() and not user.is_staff  # only staff allowed to see "future" editions
        ):
            raise Http404
    else:
        date_published = None

    if publication.slug != settings.DEFAULT_PUB:
        if date_published:
            edition = get_object_or_404(Edition, date_published=date_published, publication=publication)
        else:
            edition = get_current_edition(publication=publication)
        top_articles = edition.top_articles if edition else []
        context.update({'edition': edition, 'allow_ads': getattr(settings, 'HOMEV3_NON_DEFAULT_PUB_ALLOW_ADS', True)})
        template = getattr(settings, 'HOMEV3_NON_DEFAULT_PUB_TEMPLATE', 'index_pubs.html')
    else:
        if date_published:
            try:
                ld_edition = get_object_or_404(
                    Edition,
                    date_published=date_published,
                    publication__slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL,
                )
            except Edition.MultipleObjectsReturned:
                ld_edition = get_object_or_404(Edition, date_published=date_published, publication=publication)
        else:
            # get edition as usual
            ld_edition = get_current_edition()
            # unsubscribed newsletters header content.
            if (
                is_authenticated
                and getattr(settings, 'HOMEV3_NEWSLETTERS_HEADER_ENABLED', False)
                and (
                    getattr(settings, 'HOMEV3_NEWSLETTERS_HEADER_ENABLED_MOBILE', False)
                    or not get_user_agent(request).is_mobile
                )
                and not request.session.get("unsubscribed_nls_notice_closed")
                and user_has_subscriber
                and user.email
                and user.email not in bouncer_blocklisted
            ):
                context["unsubscribed_newsletters"] = unsubscribed_newsletters(user.subscriber)

        top_articles = ld_edition.top_articles if ld_edition else []

        try:
            context['event'] = LiveEmbedEvent.objects.get(active=True, in_home=True)
        except LiveEmbedEvent.DoesNotExist:
            pass

        if settings.DEBUG:
            print('DEBUG: Default home page view called.')

        context.update(
            {
                'edition': ld_edition,
                'allow_ads': True,
                'publications': Publication.objects.filter(public=True),
                'home_publications': settings.HOME_PUBLICATIONS,
            }
        )
        template = 'index.html'

    if top_articles:

        if is_authenticated:
            ctx_update_article_extradata(context, user, user_has_subscriber, follow_set, top_articles)

        cover_article = top_articles[0]
        top_articles.pop(0)

    else:
        cover_article = None

    context.update(
        {
            'is_portada': True,
            'cover_article': cover_article,
            'destacados': top_articles,
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
