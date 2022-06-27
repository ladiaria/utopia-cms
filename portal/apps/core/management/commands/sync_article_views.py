# -*- coding: utf-8 -*-
# utopia-cms 2020,2021. Aníbal Pacheco.
from django.core.management import BaseCommand
from django.core.cache import cache
from django.db import connection

from apps import mongo_db
from core.models import Article, ArticleViews


class Command(BaseCommand):
    help = "Sync article views and reset view counters in cached table"

    def handle(self, *args, **options):
        vlevel = options.get('verbosity')
        aviews = mongo_db.core_articlevisits.find({'views': {'$gt': 0}})
        updates = {}
        for av in aviews:
            try:
                article_id = av.get('article')
                if Article.objects.filter(id=article_id).exists():
                    updates[article_id] = av.get('views')
                    mongo_db.core_articlevisits.update_one({'article': article_id}, {'$set': {'views': 0}})
                else:
                    # deleted article, remove the entry from mongo
                    if vlevel > 1:
                        print('removing deleted article %d from mongo' % article_id)
                    mongo_db.core_articlevisits.delete_one({'article': article_id})
            except Exception as e:
                print(e)
        if updates:
            # build and exec insert and update sqls (for ArticleViews and Article models)
            # NOTE: ArticleViews will take today as the date viewed for all views synced
            articleviews_table, article_table = ArticleViews._meta.db_table, Article._meta.db_table
            insert_query = """
                INSERT INTO %s(article_id,day,views) VALUES %s ON DUPLICATE KEY UPDATE views=views+VALUES(views)
            """ % (articleviews_table, ','.join('(%d,CURRENT_DATE,%d)' % t for t in updates.items()))
            article_ids = ','.join(str(k) for k in updates.keys())
            update_query = "UPDATE %s SET views=views+ELT(FIELD(id,%s),%s) WHERE id IN (%s)" % (
                article_table, article_ids, ','.join(str(k) for k in updates.values()), article_ids,
            )
            try:
                with connection.cursor() as cursor:
                    try:
                        cursor.execute(insert_query)
                    except Exception:
                        print('ERROR inserting/updating %s table, query:\n%s' % (articleviews_table, insert_query))
                    try:
                        cursor.execute(update_query)
                    except Exception:
                        print('ERROR updating %s table, query:\n%s' % (article_table, update_query))
            except Exception:
                print('ERROR: sql queries were not executed:\n%s\n%s' % (insert_query, update_query))
        # clear cache at the end
        cache.clear()
        if vlevel > 1:
            print('Sync completed.')
