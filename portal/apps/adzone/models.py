# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence
import os

from django.db import models
from django.urls import reverse
from django.utils.timezone import now, timedelta
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from .managers import AdManager


def get_default_stop_showing():
    return now() + timedelta(days=30)


class Advertiser(models.Model):
    """ A Model for our Advertiser.  """
    company_name = models.CharField(
        verbose_name=_('Company Name'), max_length=255)
    website = models.URLField(verbose_name=_('Company Site'))
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Ad Provider')
        verbose_name_plural = _('Advertisers')
        ordering = ('company_name',)

    def __str__(self):
        return self.company_name

    def get_website_url(self):
        return self.website


class AdCategory(models.Model):
    """ a Model to hold the different Categories for adverts """
    title = models.CharField(verbose_name=_('Title'), max_length=255)
    slug = models.SlugField(verbose_name=_('Slug'), unique=True)
    description = models.TextField(verbose_name=_('Description'))

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ('title',)

    def __str__(self):
        return self.title


class AdZone(models.Model):
    """ a Model that describes the attributes and behaviours of ad zones """
    title = models.CharField(verbose_name=_('Title'), max_length=255)
    slug = models.SlugField(verbose_name=_('Slug'))
    description = models.TextField(verbose_name=_('Description'))

    class Meta:
        verbose_name = 'Zone'
        verbose_name_plural = 'Zones'
        ordering = ('title',)

    def __str__(self):
        return self.title


class AdBase(models.Model):
    """
    This is our base model, from which all ads will inherit.
    The manager methods for this model will determine which ads to
    display return etc.
    """
    title = models.CharField(verbose_name=_('Title'), max_length=255)
    url = models.URLField(
        max_length=500,
        verbose_name=_('Advertised URL'),
        help_text=_('Siempre debe comenzar con http:// o https:// y si se necesita un timestamp usar %(timestamp)d'),
    )
    mobile_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Alternative Advertised URL for mobile.'),
        help_text=_('Ídem anterior. Si es la misma dejar en blanco.'),
    )
    analytics_tracking = models.CharField(verbose_name='Trackeo analytics', max_length=255, blank=True)
    since = models.DateTimeField(verbose_name=_('Since'), auto_now_add=True)
    updated = models.DateTimeField(verbose_name=_('Updated'), auto_now=True)

    start_showing = models.DateTimeField(verbose_name=_('Start showing'), default=now)
    stop_showing = models.DateTimeField(verbose_name=_('Stop showing'), default=get_default_stop_showing)

    # Relations
    advertiser = models.ForeignKey(Advertiser, on_delete=models.CASCADE, verbose_name=_("Ad Provider"))
    category = models.ForeignKey(
        AdCategory, on_delete=models.CASCADE, verbose_name=_("Category"), blank=True, null=True
    )
    zone = models.ForeignKey(AdZone, on_delete=models.CASCADE, verbose_name=_("Zone"))

    # Our Custom Manager
    objects = AdManager()

    sites = models.ManyToManyField(Site)

    class Meta:
        verbose_name = _('Ad Base')
        verbose_name_plural = _('Ads Base')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('adzone_ad_view', args=[self.id, self.analytics_tracking])

    def impressions_count(self):
        return self.adimpression_set.count()
    impressions_count.short_description = _('impressions')

    def clicks_count(self):
        return self.adclick_set.count()
    clicks_count.short_description = _('clicks')

    def intersects_show_interval(self, start_showing, stop_showing):
        latest_start = max(self.start_showing, start_showing)
        earliest_end = min(self.stop_showing, stop_showing)
        return latest_start <= earliest_end


class AdImpression(models.Model):
    """
    The AdImpression Model will record every time the ad is loaded on a page
    """
    impression_date = models.DateTimeField(
        verbose_name=_('When'), auto_now_add=True)
    source_ip = models.GenericIPAddressField(
        verbose_name=_('Who'), null=True, blank=True)
    ad = models.ForeignKey(AdBase, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Ad Impression')
        verbose_name_plural = _('Ad Impressions')


class AdClick(models.Model):
    """
    The AdClick model will record every click that a add gets
    """
    click_date = models.DateTimeField(
        verbose_name=_('When'), auto_now_add=True)
    source_ip = models.GenericIPAddressField(
        verbose_name=_('Who'), null=True, blank=True)
    ad = models.ForeignKey(AdBase, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Ad Click')
        verbose_name_plural = _('Ad Clicks')


# Example Ad Types
class TextAd(AdBase):
    """ A most basic, text based advert """
    content = models.TextField(verbose_name=_('Content'))


class BannerAd(AdBase):
    """ A standard banner Ad """
    content = models.ImageField(verbose_name=_('Banner escritorio'), upload_to="adzone/bannerads/")
    mobile_content = models.ImageField(
        verbose_name=_('Banner móvil'), upload_to="adzone/bannerads/", null=True, blank=True
    )

    def content_basename(self):
        return os.path.basename(str(self.content))

    def mobile_content_basename(self):
        return os.path.basename(str(self.mobile_content))

    class Meta:
        verbose_name = "banner"
        verbose_name_plural = "banners"
