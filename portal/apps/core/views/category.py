# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import sys
from os.path import join
import locale
import socket
from datetime import date, datetime, timedelta
import traceback
import json
from pydoc import locate
from hashids import Hashids
from favit.utils import is_xhr

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, HttpResponsePermanentRedirect, Http404
from django.views.decorators.cache import never_cache
from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from libs.utils import decode_hashid, nl_serialize_multi
from thedaily.models import Subscriber
from faq.models import Topic
from ..models import Category, CategoryNewsletter, CategoryHome, Section, Article, get_latest_edition
from ..utils import get_category_template
from ..templatetags.ldml import remove_markup


# Initialize the hashid object with salt from settings and custom length
hashids = Hashids(settings.HASHIDS_SALT, 32)


@never_cache
def category_detail(request, slug):

    category, inner_sections, questions_topic = get_object_or_404(Category, slug=slug), [], None
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
        try:
            questions_topic = Topic.published.get(slug=slug)
        except Topic.DoesNotExist:
            pass

    return render(
        request,
        get_category_template(slug),
        {
            'category': category,
            'cover_article': category_home.cover(),
            'destacados': category_home.non_cover_articles(),
            'is_portada': slug not in getattr(settings, 'CORE_CATEGORY_DETAIL_FORCE_IS_PORTADA_OFF', ()),
            'featured_section1': featured_section1,
            'featured_section2': featured_section2,
            'featured_section3': featured_section3,
            'inner_sections': inner_sections,
            'edition': get_latest_edition(),
            'questions_topic': questions_topic,
            'big_photo': category.full_width_cover_image,
            'site_description': (
                category.meta_description
                or (
                    "Portada de %s de %s con las últimas noticias, artículos y entrevistas relacionados con la "
                    "temática." % (category, Site.objects.get_current().name)
                )
            ),
        },
    )


@never_cache
def newsletter_preview(request, slug):

    # allow only staff members or requests from localhost
    if not (
        request.user.is_staff
        or request.META.get('REMOTE_ADDR')
        in (socket.gethostbyname('localhost'), socket.gethostbyname(socket.gethostname()))
    ):
        raise PermissionDenied

    # removed or changed categories redirects by settings
    category_redirections = getattr(settings, 'CORE_CATEGORY_REDIRECT', {})
    if slug in category_redirections:
        redirect_slug = category_redirections[slug]
        if redirect_slug and not redirect_slug.startswith('/'):
            return HttpResponsePermanentRedirect(reverse('category-nl-preview', args=(redirect_slug,)))

    site = Site.objects.get_current()
    category = get_object_or_404(Category, slug=slug)
    context = {
        'category': category,
        'newsletter_campaign': category.slug,
        "request_is_xhr": is_xhr(request),
    }
    render_kwargs = {"context": context}
    template_name = None

    try:

        assert slug not in getattr(settings, "SENDNEWSLETTER_CATEGORY_DISALLOW_DEFAULT_CMD", ()), \
            "The newsletter of this area (if any) is not allowed be previewed using the area newsletter preview URL"

        if not category.has_newsletter:
            context["preview_warn"] = "The 'has_newsletter' attribute for this area is not checked"

        try:
            category_nl = CategoryNewsletter.objects.get(category=category, valid_until__gt=datetime.now())
            cover_article, featured_article = category_nl.cover(), category_nl.featured_article()
            context.update(
                {
                    'articles': nl_serialize_multi(
                        [(a, False) for a in category_nl.non_cover_articles()], category, dates=False
                    ),
                    'featured_articles': nl_serialize_multi(
                        category_nl.non_cover_featured_articles(), category, dates=False
                    ),
                }
            )

        except CategoryNewsletter.DoesNotExist:

            category_home = CategoryHome.objects.get(category=category)

            cover_article = category_home.cover()
            cover_article_section = cover_article.get_section(category) if cover_article else None
            top_articles = [(a, False) for a in category_home.non_cover_articles()]

            listonly_section = getattr(settings, 'CORE_CATEGORY_NEWSLETTER_LISTONLY_SECTIONS', {}).get(category.slug)
            if listonly_section:
                top_articles = [
                    t for t in top_articles if getattr(t[0].get_section(category), "slug", None) == listonly_section
                ]
                if getattr(cover_article_section, "slug", None) != listonly_section:
                    cover_article = top_articles.pop(0)[0] if top_articles else None

            featured_article_id = getattr(settings, 'NEWSLETTER_FEATURED_ARTICLE', False)
            nl_featured = (
                Article.objects.filter(id=featured_article_id)
                if featured_article_id
                else get_latest_edition().newsletter_featured_articles()
            )
            opinion_article = nl_featured[0] if nl_featured else None

            # featured_article (a featured section in the category)
            try:
                featured_section, days_ago = settings.CORE_CATEGORY_NEWSLETTER_FEATURED_SECTIONS[category.slug]
                featured_article = category.section_set.get(slug=featured_section).latest_article()[0]
                assert featured_article.date_published >= datetime.now() - timedelta(days_ago)
            except (KeyError, Section.DoesNotExist, Section.MultipleObjectsReturned, IndexError, AssertionError):
                featured_article = None

            context.update(
                {
                    'opinion_article': nl_serialize_multi(opinion_article, category, True, False),
                    'articles': nl_serialize_multi(top_articles, category, dates=False),
                }
            )

        try:
            hashed_id = hashids.encode(int(request.user.subscriber.id))
        except AttributeError:
            hashed_id = hashids.encode(0)

        custom_subject = category.newsletter_automatic_subject is False and category.newsletter_subject
        email_subject = custom_subject or (
            getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_PREFIX', {}).get(category.slug, '')
        )
        if not custom_subject:
            subject_call = getattr(settings, 'CORE_CATEGORY_NL_SUBJECT_CALLABLE', {}).get(category.slug, None)
            email_subject += \
                locate(subject_call)() if subject_call else remove_markup(getattr(cover_article, "headline", ""))

        email_from = '%s <%s>' % (
            category.newsletter_from_name or (
                site.name
                if category.slug in getattr(settings, 'CORE_CATEGORY_NL_FROM_NAME_SITEONLY', ())
                else ('%s %s' % (site.name, category.name))
            ),
            category.newsletter_from_email or settings.NOTIFICATIONS_FROM_ADDR1,
        )

        headers = {'From': email_from, 'Subject': email_subject}

        site_url = '%s://%s' % (settings.URL_SCHEME, settings.SITE_DOMAIN)
        as_news = request.GET.get("as_news", "0").lower() in ("true", "1")
        if as_news:
            unsubscribe_url = '%s/usuarios/perfil/disable/allow_news/%s/' % (site_url, hashed_id)
        else:
            unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
                '&utm_campaign=%s&utm_content=unsubscribe' % (site_url, category.slug, hashed_id, category.slug)
        headers['List-Unsubscribe'] = '<%s>' % unsubscribe_url
        headers['List-Unsubscribe-Post'] = "List-Unsubscribe=One-Click"
        locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)

        context.update(
            {
                'site_url': site_url,
                'hashed_id': hashed_id,
                "as_news": as_news,
                'unsubscribe_url': unsubscribe_url,
                'custom_subject': custom_subject,
                'headers_preview': headers,
                'nl_date': "{d:%A} {d.day} de {d:%B de %Y}".format(d=date.today()).capitalize(),
                'cover_article': nl_serialize_multi(cover_article, category, True, False),
                'featured_article': nl_serialize_multi(featured_article, category, True, False),
            }
        )

        # override is_subscriber_any and _default only to "False"
        for suffix in ('any', 'default'):
            is_subscriber_var = 'is_subscriber_' + suffix
            is_subscriber_val = request.GET.get(is_subscriber_var)
            if is_subscriber_val and is_subscriber_val.lower() in ('false', '0'):
                context[is_subscriber_var] = False

        template_name = get_category_template(slug, "newsletter")

    except Exception as e:
        if settings.DEBUG:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(exc_type)
            print(exc_value)
            print(traceback.extract_tb(exc_traceback))
        if "headers_preview" not in context:
            context["headers_preview"] = True
        template_name, context["preview_err"] = "newsletter/error.html", e
        render_kwargs["status"] = 406

    return render(request, template_name, **render_kwargs)


@never_cache
def newsletter_browser_preview(request, slug, hashed_id=None):
    category = get_object_or_404(Category, slug=slug)
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
    for a in context['articles']:
        try:
            dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
            a['date_published'] = dp_article
        except TypeError:
            pass
        else:
            dp_articles.append((a, False))
    context['articles'] = dp_articles
    if 'featured_articles' in context:
        dp_featured_articles = []
        for a in context['featured_articles']:
            try:
                dp_article = datetime.strptime(a['date_published'], '%Y-%m-%d').date()
                a['date_published'] = dp_article
            except TypeError:
                pass
            dp_featured_articles.append(a)
        context['featured_articles'] = dp_featured_articles
    site_url = context['site_url']
    as_news = request.GET.get("as_news", "0").lower() in ("true", "1")
    if hashed_id:
        if as_news:
            unsubscribe_url = '%s/usuarios/perfil/disable/allow_news/%s/' % (site_url, hashed_id)
        else:
            unsubscribe_url = '%s/usuarios/nlunsubscribe/c/%s/%s/?utm_source=newsletter&utm_medium=email' \
                '&utm_campaign=%s&utm_content=unsubscribe' % (site_url, slug, hashed_id, slug)
        context['unsubscribe_url'] = unsubscribe_url
    # TODO: obtain missing vars from hashed_id subscriber (TODO: which are those vars?)
    context.update(
        {
            "category": category,
            "browser_preview": True,
            "as_news": as_news,
            'hashed_id': hashed_id,
            'subscriber_id': subscriber.id,
            'is_subscriber': subscriber.is_subscriber(),
            'is_subscriber_any': subscriber.is_subscriber_any(),
            'is_subscriber_default': subscriber.is_subscriber(settings.DEFAULT_PUB),
        }
    )
    return render(request, get_category_template(slug, "newsletter"), context)


@never_cache
@login_required
def nl_browser_authpreview(request, slug):
    """ wrapper view for the special url pattern for authenticated users """
    return newsletter_browser_preview(request, slug)
