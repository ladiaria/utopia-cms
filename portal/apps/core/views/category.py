# -*- coding: utf-8 -*-
import sys
from os.path import join
import locale
import socket
from datetime import date, datetime, timedelta
import traceback
import json
from hashids import Hashids

from django.conf import settings
from django.http import HttpResponseServerError, HttpResponseForbidden, HttpResponsePermanentRedirect, Http404
from django.views.decorators.cache import never_cache
from django.contrib.sites.models import Site
from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse

from libs.utils import decode_hashid

from core.models import Category, CategoryNewsletter, CategoryHome, Section, Article, get_latest_edition
from core.templatetags.ldml import remove_markup
from thedaily.models import Subscriber
from faq.models import Question, Topic


# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


@never_cache
def category_detail(request, slug):

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

    for inner_section_slug in getattr(settings, 'CORE_CATEGORY_INNER_SECTIONS', {}).get(slug, ()):
        try:
            inner_sections.append(category.section_set.get(slug=inner_section_slug))
        except Section.DoesNotExist:
            pass

    if slug in getattr(settings, 'CORE_CATEGORIES_ENABLE_QUESTIONS', ()):
        question_list = Question.published.filter(topic__slug=slug)
        try:
            questions_topic = Topic.objects.get(slug=slug)
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
        socket.gethostbyname('localhost'), socket.gethostbyname(socket.gethostname()))
    ):
        return HttpResponseForbidden()

    # removed or changed categories redirects by settings
    category_redirections = getattr(settings, 'CORE_CATEGORY_REDIRECT', {})
    if slug in category_redirections:
        redirect_slug = category_redirections[slug]
        if redirect_slug:
            return HttpResponsePermanentRedirect(
                reverse('category-nl-preview', args=(settings.CORE_CATEGORY_REDIRECT[slug], ))
            )

    site = Site.objects.get_current()
    category = get_object_or_404(Category, slug=slug)

    try:

        context = {'category': category, 'newsletter_campaign': category.slug}

        try:
            category_nl = CategoryNewsletter.objects.get(category=category, valid_until__gt=datetime.now())
            cover_article, featured_article = category_nl.cover(), category_nl.featured_article()
            context.update(
                {
                    'cover_article_section': cover_article.publication_section() if cover_article else None,
                    'articles': [(a, a.publication_section()) for a in category_nl.non_cover_articles()],
                    'featured_article_section': featured_article.publication_section() if featured_article else None,
                    'featured_articles':
                        [(a, a.publication_section()) for a in category_nl.non_cover_featured_articles()],
                }
            )

        except CategoryNewsletter.DoesNotExist:

            category_home = get_object_or_404(CategoryHome, category=category)

            cover_article = category_home.cover()
            cover_article_section = cover_article.publication_section() if cover_article else None
            top_articles = [(a, a.publication_section()) for a in category_home.non_cover_articles()]

            listonly_section = getattr(settings, 'CORE_CATEGORY_NEWSLETTER_LISTONLY_SECTIONS', {}).get(category.slug)
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
                featured_section, days_ago = settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS[category.slug]
                featured_article = category.section_set.get(slug=featured_section).latest_article()[0]
                assert (featured_article.date_published >= datetime.now() - timedelta(days_ago))
            except (KeyError, Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError, AssertionError):
                featured_article = None

            context.update(
                {
                    'opinion_article': opinion_article,
                    'cover_article_section': cover_article_section,
                    'articles': top_articles,
                }
            )

        try:
            hashed_id = hashids.encode(int(request.user.subscriber.id))
        except AttributeError:
            hashed_id = hashids.encode(0)

        custom_subject = category.newsletter_automatic_subject is False and category.newsletter_subject
        email_subject = custom_subject or (
            getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_PREFIX', {}).get(category.slug, u'')
            + remove_markup(cover_article.headline)
        )

        email_from = u'%s <%s>' % (
            site.name if category.slug in getattr(
                settings, 'CORE_CATEGORY_NL_FROM_NAME_SITEONLY', ()
            ) else (u'%s %s' % (site.name, category.name)),
            settings.NOTIFICATIONS_FROM_ADDR1,
        )

        headers = {'From': email_from, 'Subject': email_subject}

        site_url = '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN)
        unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
            '&utm_campaign=%s&utm_content=unsubscribe' % (site_url, category.slug, hashed_id, category.slug)
        headers['List-Unsubscribe'] = headers['List-Unsubscribe-Post'] = '<%s>' % unsubscribe_url
        locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)

        context.update(
            {
                'site_url': site_url,
                'hashed_id': hashed_id,
                'unsubscribe_url': unsubscribe_url,
                'custom_subject': custom_subject,
                'headers_preview': headers,
                'nl_date': "{d:%A} {d.day} de {d:%B de %Y}".format(d=date.today()).capitalize(),
                'cover_article': cover_article,
                'enable_photo_byline': settings.CORE_ARTICLE_ENABLE_PHOTO_BYLINE,
                'featured_article': featured_article,
            }
        )

        # override is_subscriber_any and _default only to "False"
        for suffix in ('any', 'default'):
            is_subscriber_var = 'is_subscriber_' + suffix
            is_subscriber_val = request.GET.get(is_subscriber_var)
            if is_subscriber_val and is_subscriber_val.lower() in (u'false', u'0'):
                context[is_subscriber_var] = False

        return render(request, '%s/newsletter/%s.html' % (settings.CORE_CATEGORIES_TEMPLATE_DIR, slug), context)

    except Exception as e:
        if settings.DEBUG:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(exc_type)
            print(exc_value)
            print(traceback.extract_tb(exc_traceback))
        return HttpResponseServerError(u'ERROR: %s' % e)


@never_cache
def newsletter_browser_preview(request, slug, hashed_id):
    decoded = decode_hashid(hashed_id)
    # TODO: if authenticated => assert same logged in user
    if decoded:
        subscriber = get_object_or_404(Subscriber, id=decoded[0])
        if not subscriber.user:
            raise Http404
    else:
        raise Http404
    try:
        context = json.loads(open(join(settings.SENDNEWSLETTER_EXPORT_DIR, '%s_ctx.json' % slug)).read())
    except IOError:
        raise Http404
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
        dp_articles.append((a, a_section))
    context['articles'] = dp_articles
    if 'featured_articles' in context:
        dp_featured_articles = []
        for a, a_section in context['featured_articles']:
            dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
            a['date_published'] = dp_article
            dp_featured_articles.append((a, a_section))
        context['featured_articles'] = dp_featured_articles
    site_url = context['site_url']
    unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
        '&utm_campaign=%s&utm_content=unsubscribe' % (site_url, slug, hashed_id, slug)
    # TODO: obtain missing vars from hashed_id subscriber
    context.update(
        {
            'hashed_id': hashed_id,
            'unsubscribe_url': unsubscribe_url,
            'subscriber_id': subscriber.id,
            'is_subscriber': subscriber.is_subscriber(),
            'is_subscriber_any': subscriber.is_subscriber_any(),
            'is_subscriber_default': subscriber.is_subscriber(settings.DEFAULT_PUB),
        }
    )
    return render(request, '%s/newsletter/%s.html' % (settings.CORE_CATEGORIES_TEMPLATE_DIR, slug), context)
