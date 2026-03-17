# -*- coding: utf-8 -*-
# utopia-cms 2020-2026. Aníbal Pacheco.

from django.core.management import BaseCommand
from django.db.utils import IntegrityError
from django.utils.timezone import make_aware, utc

from apps import mongo_db
from core.models import ArticleViewedBy


class Command(BaseCommand):
    help = "Moves article viewed by data from mongodb to Django model"

    def handle(self, *args, **options):
        mdb_view = mongo_db.core_articleviewedby.find_one_and_delete({})
        while mdb_view:
            viewed_at = make_aware(mdb_view['viewed_at'], utc)
            try:
                avb = ArticleViewedBy.objects.get(article=mdb_view['article'], user=mdb_view['user'])
                avb.viewed_at = viewed_at
                avb.save()
            except ArticleViewedBy.DoesNotExist:
                try:
                    ArticleViewedBy.objects.create(
                        article_id=mdb_view['article'], user_id=mdb_view['user'], viewed_at=viewed_at
                    )
                except IntegrityError:
                    pass
            mdb_view = mongo_db.core_articleviewedby.find_one_and_delete({})
