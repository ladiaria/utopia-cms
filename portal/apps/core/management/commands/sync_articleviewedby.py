# -*- coding: utf-8 -*-
# utopia-cms 2020-24. Aníbal Pacheco.
from django.core.management import BaseCommand
from django.db.utils import IntegrityError
from django.utils.timezone import make_aware

from apps import mongo_db
from core.models import ArticleViewedBy


class Command(BaseCommand):
    help = "Moves article viewed by data from mongodb to Django model"

    def handle(self, *args, **options):
        mdb_view = mongo_db.core_articleviewedby.find_one_and_delete({})
        while mdb_view:
            try:
                article, user = mdb_view['article'], mdb_view['user']
                viewed_at = make_aware(mdb_view['viewed_at'])
                avb = ArticleViewedBy.objects.get(article=article, user=user)
                avb.viewed_at = viewed_at
                avb.save()
            except ArticleViewedBy.DoesNotExist:
                try:
                    ArticleViewedBy.objects.create(article_id=article, user_id=user, viewed_at=viewed_at)
                except IntegrityError:
                    pass
            mdb_view = mongo_db.core_articleviewedby.find_one_and_delete({})
        # warn if inconsistencies are found
        if ArticleViewedBy.objects.raw(
            """
            SELECT avb.id, COUNT(*) AS count FROM core_articleviewedby avb LEFT JOIN core_article a ON article_id=a.id
            WHERE a.id IS NULL LIMIT 1
            """
        )[0].count and options.get('verbosity'):
            print(
                "WARNING: References to non-existent articles found in article-viewed-by data, consider deleting them "
                "executing the following SQL command in the database:\n  "
                "DELETE FROM core_articleviewedby WHERE NOT EXISTS (SELECT id FROM core_article WHERE id=article_id);"
            )
