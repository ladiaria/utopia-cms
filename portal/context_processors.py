# -*- coding: utf-8 -*-

import pycountry

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
    url_dict.update({'URL_SCHEME': settings.URL_SCHEME, "SITE_URL_SD": settings.SITE_URL_SD})
    return url_dict


def gtm(request):
    return {
        'GTM_CONTAINER_ID': settings.GTM_CONTAINER_ID,
        'GTM_AMP_CONTAINER_ID': getattr(settings, "GTM_AMP_CONTAINER_ID", None),
        'GA_MEASUREMENT_ID': settings.GA_MEASUREMENT_ID,
    }


def site(request):
    result = {
        'country_name': pycountry.countries.get(alpha_2=settings.LOCAL_COUNTRY).name,
        "base_template": getattr(settings, "PORTAL_BASE_TEMPLATE", "base.html"),
        "title_append_country": settings.PORTAL_TITLE_APPEND_COUNTRY,
        "admin_dark_mode_vars_template": getattr(
            settings, "PORTAL_ADMIN_DARK_MODE_VARS_TEMPLATE", "admin/admin_dark_mode_vars_template.html",
        ),
        "admin_martor_change_form_custom_css": getattr(settings, "PORTAL_ADMIN_CHANGE_FORM_MARTOR_CUSTOM_CSS", None),
    }
    try:
        site = Site.objects.get_current()
        result.update(
            {
                'site': site,
                'meta_robots_content': 'noindex' if any(
                    ['/' in r.disallowed.values_list('pattern', flat=True) for r in site.rule_set.all()]
                ) else 'all',
                'site_description': getattr(settings, 'HOMEV3_SITE_DESCRIPTION', site.name),
            }
        )
    except Site.DoesNotExist:
        pass
    return result


def publications(request):
    DEFAULT_PUB = settings.DEFAULT_PUB
    try:
        default_pub = Publication.objects.get(slug=DEFAULT_PUB)
    except Publication.DoesNotExist:
        default_pub = None

    result = {
        'DEFAULT_PUB': DEFAULT_PUB,
        'default_pub': default_pub,
        'custom_icons_publications': getattr(settings, 'CORE_CUSTOM_ICONS_PUBLICATIONS', None),
    }

    for p in Publication.objects.exclude(slug=DEFAULT_PUB).iterator():
        slug_var = p.slug.replace('-', '_')
        result.update({slug_var.upper() + '_SUB': p.slug, slug_var + '_pub': p})

    is_amp_detect = getattr(request, "is_amp_detect", False)
    result['extra_header_template'] = getattr(
        settings, 'HOMEV3_EXTRA_HEADER_TEMPLATE%s' % ('_AMP' if is_amp_detect else ''), None
    )
    if not is_amp_detect:
        result['footer_template'] = settings.HOMEV3_FOOTER_TEMPLATE
        result['subscribe_notice_template'] = getattr(
            settings, "HOMEV3_SUBSCRIBE_NOTICE_TEMPLATE", "homev3/templates/subscribe_notice.html"
        )

    # use this context processor to load also some other useful variables configured in settings
    result['PWA_ENABLED'] = getattr(settings, 'PWA_ENABLED', True)
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
    Fills context variables to be shown or needed in the main menus and other features.
    Also fill another context variables using to the visualization of many UX "modules".
    """
    categories_with_order = Category.objects.filter(order__isnull=False)
    result = {
        'MENU_CATEGORIES': dict((c, c.section_set.all() if c.dropdown_menu else None) for c in categories_with_order),
        "categories_with_order": [c.slug for c in categories_with_order],
        'CORE_PUSH_NOTIFICATIONS_OFFER': settings.CORE_PUSH_NOTIFICATIONS_OFFER,
        'CORE_PUSH_NOTIFICATIONS_VAPID_PUBKEY': settings.CORE_PUSH_NOTIFICATIONS_VAPID_PUBKEY,
        'push_notifications_keys_set': bool(
            settings.CORE_PUSH_NOTIFICATIONS_VAPID_PUBKEY and settings.CORE_PUSH_NOTIFICATIONS_VAPID_PRIVKEY
        ),
        'MOBILE_NAV_EXTRA_TEMPLATE': getattr(settings, 'HOMEV3_MOBILE_NAV_EXTRA_TEMPLATE', None),
        'LOGIN_NO_REDIRECT_URLPATHS': ['/usuarios/sesion-cerrada/', '/usuarios/error/login/', '/admin/logout/'],
        'MENU_PUBLICATIONS':
            Publication.objects.filter(public=True, is_emergente=True).exclude(slug=settings.DEFAULT_PUB),
        'MENU_PUBLICATIONS_MORE_EXTRA': Publication.objects.filter(
            public=True, is_emergente=False
        ).exclude(slug__in=getattr(settings, 'HOMEV3_EXCLUDE_MENU_PUBLICATIONS', (settings.DEFAULT_PUB, ))),
        "article_card_read_later_enabled": getattr(settings, 'CORE_ENABLE_ARTICLE_CARD_READ_LATER', True),
        "article_card_lock_tooltip_enabled": getattr(settings, 'CORE_ENABLE_ARTICLE_CARD_LOCK_TOOLTIP', True),
    }

    mobile_nav_search = getattr(settings, 'HOMEV3_MOBILE_NAV_SEARCH', 1)
    mobile_nav_latest_article = getattr(settings, 'HOMEV3_MOBILE_NAV_LATEST_ARTICLE', 1)
    mobile_nav_ths = 3 + mobile_nav_search + getattr(settings, 'HOMEV3_MOBILE_NAV_EXTRA_THS', 0)

    menu_lal = getattr(settings, 'HOMEV3_LATEST_ARTICLE_LINKS', ())
    if menu_lal:
        result['MENU_LATEST_ARTICLE_LINKS'] = menu_lal
        mobile_nav_ths += mobile_nav_latest_article
        if len(menu_lal) > 1:
            result['MENU_LATEST_ARTICLE_LINKS_DROPDOWN'] = getattr(
                settings, 'HOMEV3_LATEST_ARTICLE_LINKS_DROPDOWN', 'latest'
            )

    result.update(
        {
            'mobile_nav_ths': mobile_nav_ths,
            'mobile_nav_search': mobile_nav_search,
            "mobile_nav_latest_article": mobile_nav_latest_article,
            'mobile_nav_detail_more': getattr(settings, 'HOMEV3_MOBILE_NAV_DETAIL_MORE', 1) or 0,
        }
    )
    return result


def article_content_type(request):
    return {'article_ct_id': ContentType.objects.get_for_model(Article).id}
