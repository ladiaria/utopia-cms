# -*- coding: utf-8 -*-
# utopia-cms 2020. Aníbal Pacheco.

from django.core.management import BaseCommand
from django.db.utils import IntegrityError

from apps import core_articleviewedby_mdb
from core.models import ArticleViewedBy


class Command(BaseCommand):
    help = "Moves article viewed by data from mongodb to Django model"

    def handle(self, *args, **options):
        mdb_view = core_articleviewedby_mdb.posts.find_one_and_delete({})
        while mdb_view:
            try:
                avb = ArticleViewedBy.objects.get(article=mdb_view['article'], user=mdb_view['user'])
                avb.viewed_at = mdb_view['viewed_at']
                avb.save()
            except ArticleViewedBy.DoesNotExist:
                try:
                    ArticleViewedBy.objects.create(
                        article_id=mdb_view['article'], user_id=mdb_view['user'], viewed_at=mdb_view['viewed_at'])
                except IntegrityError:
                    pass
            mdb_view = core_articleviewedby_mdb.posts.find_one_and_delete({})
