from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.db import models
from django.utils.timezone import now


class AdManager(models.Manager):
    """ A Custom Manager for ads """

    def get_random_ad(self, ad_zone, ad_category=None, site=None):
        """
        Returns a random advert that belongs for the specified ``ad_category``
        and ``ad_zone``.
        If ``ad_category`` is None, the ad will be category independent.
        """
        qs = self.get_queryset().filter(
            start_showing__lte=now(), stop_showing__gte=now(),
            zone__slug=ad_zone, sites=site or Site.objects.get_current().pk
        ).select_related('textad', 'bannerad')
        if ad_category:
            qs = qs.filter(category__slug=ad_category)
        try:
            ad = qs.order_by('?')[0]
        except IndexError:
            return None
        return ad

    def get_rr_ad(self, ad_zone, ad_category=None, index=0):
        """
        Returns round robin next ad based on index parameter
        """
        qs = self.get_queryset().filter(
            start_showing__lte=now(),
            stop_showing__gte=now(),
            zone__slug=ad_zone,
            sites=Site.objects.get_current().pk
        ).select_related('textad', 'bannerad')
        if ad_category:
            qs = qs.filter(category__slug=ad_category)
        try:
            ad = qs.order_by('id')[(index or 0) % qs.count()]
        except (IndexError, ZeroDivisionError):
            return None
        return ad
