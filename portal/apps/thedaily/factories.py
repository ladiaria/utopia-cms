"""
An example factory class, not used.
"""
from factory.django import DjangoModelFactory
from factory import SubFactory
from content_settings.conf import content_settings

from django.conf import settings

from core.factories import PublicationFactory
from .models import SubscriptionPrices


class SubscriptionPricesFactory(DjangoModelFactory):
    class Meta:
        model = SubscriptionPrices

    subscription_type = content_settings.THEDAILY_SUBSCRIPTION_TYPE_DEFAULT
    price = 195
    order = 1
    auth_group = None
    publication = SubFactory(PublicationFactory, slug=settings.DEFAULT_PUB)
