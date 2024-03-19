# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import traceback

from django.db.models import Manager
from django.utils import timezone


def get_published_kwargs():
    return {"is_published": True, "date_published__lte": timezone.now()}


class PublishedArticleManager(Manager):
    # TODO: comment the usage of this commented attribute
    # use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().filter(**get_published_kwargs())


class DebugManager(Manager):

    def get_queryset(self):
        traceback.print_stack()
        return super().get_queryset()
