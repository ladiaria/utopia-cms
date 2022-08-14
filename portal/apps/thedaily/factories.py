"""
An example factory class, not used.
"""

from factory.django import DjangoModelFactory
from factory import SubFactory
from .models import SubscriptionPrices
from django.conf import settings
from core.factories import PublicationFactory


class SubscriptionPricesFactory(DjangoModelFactory):
    class Meta:
        model = SubscriptionPrices

    subscription_type = settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES[0][0]
    price = 195
    order = 1
    auth_group = None
    publication = SubFactory(PublicationFactory, slug=settings.DEFAULT_PUB)
