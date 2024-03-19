# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence
#
# Modifications made in utopia-cms (TODO: include them and the BSD Licence that the original author ask for)

from __future__ import unicode_literals

from random import randint

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import timezone

from apps import mongo_db

from adzone.models import AdBase, AdImpression

register = template.Library()


@register.simple_tag(takes_context=True, name='random_zone_ad')
def random_zone_ad(context, ad_zone):
    """
    Returns a random advert for ``ad_zone``.
    The advert returned is independent of the category

    In order for the impression to be saved add the following
    to the TEMPLATE_CONTEXT_PROCESSORS:

    'adzone.context_processors.get_source_ip'

    Tag usage:
    {% load adzone_tags %}
    {% random_zone_ad 'zone_slug' %}

    """
    publication_slug = context['request'].GET.get('publication', settings.DEFAULT_PUB) or settings.DEFAULT_PUB
    # This is a hack to obtain ads related to sites, the sites should use the publication slug as their domain.
    # (the special case is the default publication which must use the correct domain to have a working site)
    # TODO: change this using Publications directly (relate ads to pubs instead to sites)
    publication_slug_or_domain = settings.SITE_DOMAIN if publication_slug == settings.DEFAULT_PUB else publication_slug
    if settings.DEBUG:
        print("DEBUG: adzone_tags.random_zone_ad - publication_slug_or_domain='%s'" % publication_slug_or_domain)
    ad = AdBase.objects.get_random_ad(ad_zone, site=Site.objects.get(domain=publication_slug_or_domain))

    if ad:

        # Record a impression for the ad.
        from_ip = settings.ADZONE_LOG_AD_IMPRESSIONS and context.get('from_ip')
        if from_ip:
            try:
                mongo_db.adzone_impressions.insert_one(
                    {'ad': ad.id, 'source_ip': from_ip, 'impression_date': timezone.now()}
                )
            except Exception:
                pass

        context.update({'ad': ad})
        return template.loader.render_to_string('adzone/ad_tag.html', context=context.flatten())
    else:
        return u''


@register.inclusion_tag('adzone/ad_tag.html', takes_context=True)
def rr_zone_ad(context, ad_zone, index=0):
    """
    Returns a rr advert for ``ad_zone`` based on index.
    The advert returned is independent of the category

    In order for the impression to be saved add the following
    to the TEMPLATE_CONTEXT_PROCESSORS:

    'adzone.context_processors.get_source_ip'

    Tag usage:
    {% load adzone_tags %}
    {% rr_zone_ad 'zone_slug' index %}
    """

    # Retrieve a rr ad for the zone
    ad = AdBase.objects.get_rr_ad(ad_zone, index=index)

    # Record a impression for the ad
    if settings.ADZONE_LOG_AD_IMPRESSIONS and 'from_ip' in context and ad:
        from_ip = context.get('from_ip')
        try:
            AdImpression.objects.create(
                ad=ad, impression_date=timezone.now(), source_ip=from_ip)
        except Exception:
            pass

    return {'ad': ad}


@register.inclusion_tag('adzone/ad_tag.html', takes_context=True)
def random_category_ad(context, ad_zone, ad_category):
    """
    Returns a random advert from the specified category.

    Usage:
    {% load adzone_tags %}
    {% random_category_ad 'zone_slug' 'my_category_slug' %}

    """

    # Retrieve a random ad for the category and zone
    ad = AdBase.objects.get_random_ad(ad_zone, ad_category)

    # Record a impression for the ad
    if settings.ADZONE_LOG_AD_IMPRESSIONS and 'from_ip' in context and ad:
        from_ip = context.get('from_ip')
        try:
            AdImpression.objects.create(
                ad=ad, impression_date=timezone.now(), source_ip=from_ip)
        except Exception:
            pass

    return {'ad': ad}


@register.inclusion_tag('adzone/ad_tag.html', takes_context=True)
def rr_category_ad(context, ad_zone, ad_category, index=0):
    """
    Returns a rr advert from the specified category based on index.

    Usage:
    {% load adzone_tags %}
    {% rr_category_ad 'zone_slug' 'my_category_slug' 1 %}

    """
    to_return = {'random_int': randint(1000000, 10000000)}

    # Retrieve a rr ad for the category and zone
    ad = AdBase.objects.get_rr_ad(ad_zone, ad_category, index)
    to_return['ad'] = ad

    # Record a impression for the ad
    if settings.ADZONE_LOG_AD_IMPRESSIONS and 'from_ip' in context and ad:
        from_ip = context.get('from_ip')
        try:
            AdImpression.objects.create(
                ad=ad, impression_date=timezone.now(), source_ip=from_ip)
        except Exception:
            pass

    return to_return
