# -*- coding: utf-8 -*-
import traceback
from datetime import date

from django.db.models import Manager


class ArticleManager(Manager):
    pass


class PublishedArticleManager(ArticleManager):
    # TODO: comment the usage of this commented attribute
    # use_for_related_fields = True

    def get_query_set(self):
        return super(
            PublishedArticleManager, self).get_query_set().filter(
                is_published=True, date_published__lte=date.today()).order_by('-date_published')


class DebugManager(Manager):

    def get_query_set(self):
        traceback.print_stack()
        return super(DebugManager, self).get_query_set()
