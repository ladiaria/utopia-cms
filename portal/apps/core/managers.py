# -*- coding: utf-8 -*-
import traceback
from datetime import datetime

from django.db.models import Manager


class ArticleManager(Manager):
    pass


class PublishedArticleManager(ArticleManager):
    # TODO: comment the usage of this commented attribute
    # use_for_related_fields = True

    def get_queryset(self):
        return super(
            PublishedArticleManager, self
        ).get_queryset().filter(is_published=True, date_published__lte=datetime.now())


class DebugManager(Manager):

    def get_queryset(self):
        traceback.print_stack()
        return super(DebugManager, self).get_queryset()
