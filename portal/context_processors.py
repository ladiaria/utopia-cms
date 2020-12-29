# -*- coding: utf-8 -*-
import pycountry

from django_mobile import get_flavour

from django.conf import settings
from django.contrib.sites.models import Site

from core.models import Publication, Category


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
        'BASE_SUB': settings.BASE_SUB, 'DEFAULT_PUB': DEFAULT_PUB, 'default_pub': default_pub,
        'custom_icons_publications': getattr(settings, 'CORE_CUSTOM_ICONS_PUBLICATIONS', None)}

    for p in Publication.objects.exclude(slug=DEFAULT_PUB).iterator():
        result.update({p.slug.upper() + '_SUB': p.slug, p.slug + '_pub': p})

    if get_flavour(request) == 'amp':
        result['extra_header_template'] = getattr(settings, 'HOMEV3_EXTRA_HEADER_TEMPLATE_AMP', None)
    else:
        result['extra_header_template'] = getattr(settings, 'HOMEV3_EXTRA_HEADER_TEMPLATE', None)
        result['footer_template'] = settings.HOMEV3_FOOTER_TEMPLATE

    # use this context processor to load also some other useful variables configured in settings
    result.update((var, getattr(settings, var, None)) for var in (
        'HOMEV3_LOGO', 'HOMEV3_SECONDARY_LOGO', 'HOMEV3_LOGO_FOOTER', 'HOMEV3_LOGO_PRINTABLE', 'HOMEV3_LOGO_ALT_TEXT',
        'HOMEV3_TWITTER_SITE_META', 'HOMEV3_EXTRA_META', 'CORE_ARTICLE_DETAIL_PUBLISHER_META'))

    return result


def main_menus(request):
    """
    Fills context variables to be shown in the main menus.
    Also fill another context variables using to the visualization of many ux "modules".
    """
    result = {
        'MENU_CATEGORIES': Category.objects.filter(order__isnull=False),
        'CORE_ENABLE_MEZCLA': getattr(settings, 'CORE_ENABLE_MEZCLA', False),
        'MOBILE_NAV_EXTRA_TEMPLATE': getattr(settings, 'HOMEV3_MOBILE_NAV_EXTRA_TEMPLATE', None)}

    mobile_nav_ths = 4 + getattr(settings, 'HOMEV3_MOBILE_NAV_EXTRA_THS', 0)

    menu_lasl = getattr(settings, 'HOMEV3_LATEST_ARTICLE_SECTION_SLUG', None)
    if menu_lasl:
        result.update({
            'MENU_LATEST_ARTICLE_SECTION_SLUG': menu_lasl,
            'MENU_LATEST_ARTICLE_LINK_TEXT_S': settings.HOMEV3_LATEST_ARTICLE_LINK_TEXT_S,
            'MENU_LATEST_ARTICLE_LINK_TEXT_L': settings.HOMEV3_LATEST_ARTICLE_LINK_TEXT_L})
        mobile_nav_ths += 1

    try:
        menu_publications = Publication.objects.filter(public=True).exclude(
            slug__in=getattr(settings, 'HOMEV3_EXCLUDED_MENU_PUBLICATIONS', ()))
    except Exception:
        menu_publications = "no-menu"

    result.update({'MENU_PUBLICATIONS': menu_publications, 'mobile_nav_ths': mobile_nav_ths})
    return result
