# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence
from builtins import str
import os
import datetime

from PIL import Image
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from adzone.managers import AdManager

from django.contrib.sites.models import Site
from django.urls import reverse

# Use a datetime a few days before the max to that timezone changes don't
# cause an OverflowError.
MAX_DATETIME = datetime.datetime.max - datetime.timedelta(days=2)
try:
    from django.utils.timezone import now, make_aware, utc
except ImportError:
    now = datetime.datetime.now
else:
    MAX_DATETIME = make_aware(MAX_DATETIME, utc)


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
        verbose_name=_('Advertised URL'), help_text=_(
            'Siempre debe comenzar con http:// o https:// y si se '
            'necesita un timestamp usar %(timestamp)d'))
    mobile_url = models.URLField(
        max_length=500,
        blank=True, null=True,
        verbose_name=_('Alternative Advertised URL for mobile.'),
        help_text=_('Ídem anterior. Si es la misma dejar en blanco.'))
    analytics_tracking = models.CharField(
        verbose_name='Trackeo analytics', max_length=255, blank=True)
    since = models.DateTimeField(verbose_name=_('Since'), auto_now_add=True)
    updated = models.DateTimeField(verbose_name=_('Updated'), auto_now=True)

    start_showing = models.DateTimeField(verbose_name=_('Start showing'),
                                         default=now)
    stop_showing = models.DateTimeField(verbose_name=_('Stop showing'),
                                        default=MAX_DATETIME)

    # Relations
    advertiser = models.ForeignKey(Advertiser, on_delete=models.CASCADE, verbose_name=_("Ad Provider"))
    category = models.ForeignKey(AdCategory, on_delete=models.CASCADE,
                                 verbose_name=_("Category"),
                                 blank=True,
                                 null=True)
    zone = models.ForeignKey(AdZone, on_delete=models.CASCADE, verbose_name=_("Zone"))

    # Our Custom Manager
    objects = AdManager()

    sites = models.ManyToManyField(Site, verbose_name=(u"Sites"))

    class Meta:
        verbose_name = _('Ad Base')
        verbose_name_plural = _('Ad Bases')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('adzone_ad_view', args=[self.id, self.analytics_tracking])


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
    content = models.ImageField(
        verbose_name=_('Banner escritorio'), upload_to="adzone/bannerads/",
        help_text='Dimensiones: 970×250px</br>Tamaño máximo permitido: 150kb</br>Formato: JPG, GIF, PNG')
    mobile_content = models.ImageField(
        verbose_name=_('Banner móvil'), upload_to="adzone/bannerads/",
        help_text='Dimensiones: 300×250px</br>Tamaño máximo permitido: 150kb</br>Formato: JPG, GIF, PNG',
        null=True, blank=True)

    def content_basename(self):
        return os.path.basename(str(self.content))

    def mobile_content_basename(self):
        return os.path.basename(str(self.mobile_content))

    def clean(self):
        super().clean()

        self._validate_duplicate_zone()
        self._validate_image_dimensions(self.content, 980, 150, "content")
        self._validate_image_dimensions(self.mobile_content, 320, 100, "mobile_content")


    def _validate_duplicate_zone(self):
        duplicate_query = BannerAd.objects.filter(zone_id=self.zone_id)
        if self.pk:
            duplicate_query = duplicate_query.exclude(pk=self.pk)
        if duplicate_query.exists():
            raise ValidationError({
                "zone": f"Un BannerAd con la zona '{self.zone}' ya existe. "
                        "Por favor, seleccione otra zona."
            })

    def _validate_image_dimensions(self, image, required_width, required_height, field_name):
        if image:
            img = Image.open(image)
            width, height = img.size
            if width != required_width or height != required_height:
                raise ValidationError({
                    field_name: f"La imagen debe tener dimensiones de {required_width}×{required_height}px, "
                                f"pero tiene {width}×{height}px."
                })
