# -*- coding: utf-8 -*-
import pycountry

from django_mobile import get_flavour

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType

from core.models import Publication, Category, Article


def urls(request):
    url_dict = {}
    for attr in dir(settings):
        if attr.endswith('_URL'):
            try:
                url_dict[attr] = getattr(settings, attr).replace('%s', '')
            except AttributeError:
                pass
    url_dict['URL_SCHEME'] = settings.URL_SCHEME
    return url_dict


def gtm(request):
    return {'GTM_CONTAINER_ID': settings.GTM_CONTAINER_ID, 'GTM_AMP_CONTAINER_ID': settings.GTM_AMP_CONTAINER_ID}


def site(request):
    site = Site.objects.get_current()
    meta_robots_content = 'noindex' if any(['/' in r.disallowed_urls() for r in site.rule_set.all()]) else 'all'
    return {
        'site': site, 'meta_robots_content': meta_robots_content,
        'country_name': pycountry.countries.get(alpha2=settings.LOCAL_COUNTRY).name,
        'site_description': getattr(settings, 'HOMEV3_SITE_DESCRIPTION', site.name)}


def publications(request):
    DEFAULT_PUB = settings.DEFAULT_PUB
    try:
        default_pub = Publication.objects.get(slug=DEFAULT_PUB)
    except Publication.DoesNotExist:
        default_pub = None

    result = {
        'BASE_SUB': settings.BASE_SUB,
        'DEFAULT_PUB': DEFAULT_PUB,
        'default_pub': default_pub,
        'custom_icons_publications': getattr(settings, 'CORE_CUSTOM_ICONS_PUBLICATIONS', None),
    }

    for p in Publication.objects.exclude(slug=DEFAULT_PUB).iterator():
        slug_var = p.slug.replace('-', '_')
        result.update({slug_var.upper() + '_SUB': p.slug, slug_var + '_pub': p})

    if get_flavour(request) == 'amp':
        result['extra_header_template'] = getattr(settings, 'HOMEV3_EXTRA_HEADER_TEMPLATE_AMP', None)
    else:
        result['extra_header_template'] = getattr(settings, 'HOMEV3_EXTRA_HEADER_TEMPLATE', None)
        result['footer_template'] = settings.HOMEV3_FOOTER_TEMPLATE

    # use this context processor to load also some other useful variables configured in settings
    result.update(
        (
            (var, getattr(settings, var, None)) for var in (
                'HOMEV3_CUSTOM_CSS',
                'HOMEV3_CUSTOM_PRINT_CSS',
                'HOMEV3_LOGO',
                'HOMEV3_LOGO_WIDTH',
                'HOMEV3_SECONDARY_LOGO',
                'HOMEV3_LOGO_FOOTER',
                'HOMEV3_LOGO_FOOTER_WIDTH',
                'HOMEV3_LOGO_PRINTABLE',
                'HOMEV3_LOGO_PRINTABLE_WIDTH',
                'HOMEV3_LOGO_ALT_TEXT',
                'HOMEV3_TWITTER_SITE_META',
                'HOMEV3_EXTRA_META',
                'HOMEV3_MENU_PUBLICATIONS_USE_HEADLINE',
                'CORE_ARTICLE_DETAIL_PUBLISHER_META',
                'CORE_ARTICLE_CARDS_DATE_PUBLISHED_USE_AGO',
                'CORE_ARTICLE_DETAIL_DATE_TOOLTIP',
                'CORE_ARTICLE_DETAIL_ALL_DATE_TOOLTIP',
                'CORE_ARTICLE_ENABLE_PHOTO_BYLINE',
                'PWA_MANIFEST_STATIC_PATH',
            )
        )
    )

    return result


def main_menus(request):
    """
    Fills context variables to be shown or needed in the main menus.
    Also fill another context variables using to the visualization of many UX "modules".
    """
    result = {
        'MENU_CATEGORIES': Category.objects.filter(order__isnull=False),
        'MOBILE_NAV_EXTRA_TEMPLATE': getattr(settings, 'HOMEV3_MOBILE_NAV_EXTRA_TEMPLATE', None),
        'LOGIN_NO_REDIRECT_URLPATHS': ['/usuarios/sesion-cerrada/', '/usuarios/error/login/', '/admin/logout/'],
        'MENU_PUBLICATIONS':
            Publication.objects.filter(public=True, is_emergente=True).exclude(slug=settings.DEFAULT_PUB),
        'MENU_PUBLICATIONS_MORE_EXTRA': Publication.objects.filter(
            public=True, is_emergente=False
        ).exclude(slug__in=getattr(settings, 'HOMEV3_EXCLUDE_MENU_PUBLICATIONS', (settings.DEFAULT_PUB, ))),
    }

    mobile_nav_search = getattr(settings, 'HOMEV3_MOBILE_NAV_SEARCH', 1)
    mobile_nav_ths = 3 + mobile_nav_search + getattr(settings, 'HOMEV3_MOBILE_NAV_EXTRA_THS', 0)

    menu_lal = getattr(settings, 'HOMEV3_LATEST_ARTICLE_LINKS', ())
    if menu_lal:
        result['MENU_LATEST_ARTICLE_LINKS'] = menu_lal
        mobile_nav_ths += 1
        if len(menu_lal) > 1:
            result['MENU_LATEST_ARTICLE_LINKS_DROPDOWN'] = getattr(
                settings, 'HOMEV3_LATEST_ARTICLE_LINKS_DROPDOWN', 'latest'
            )

    result.update(
        {
            'mobile_nav_ths': mobile_nav_ths,
            'mobile_nav_search': mobile_nav_search,
            'mobile_nav_detail_more': getattr(settings, 'HOMEV3_MOBILE_NAV_DETAIL_MORE', 1) or 0,
        }
    )
    return result


def article_content_type(request):
    return {'article_ct_id': ContentType.objects.get_for_model(Article).id}
