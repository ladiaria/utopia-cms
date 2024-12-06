# -*- coding: utf-8 -*-

import traceback

from django.db.models import Manager
from django.utils import timezone


def get_published_kwargs():
    return {"is_published": True, "date_published__lte": timezone.now()}


class EditionManager(Manager):
    def get_by_natural_key(self, date_published, publication):
        return self.get(date_published=date_published, publication__slug=publication)


class SlugNaturalManager(Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class PublishedArticleManager(Manager):
    # TODO: comment the usage of this commented attribute
    # use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().filter(**get_published_kwargs())


class PublishedBreakingNewsModuleManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class DebugManager(Manager):

    def get_queryset(self):
        traceback.print_stack()
        return super().get_queryset()
