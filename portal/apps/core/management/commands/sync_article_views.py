# -*- coding: utf-8 -*-
# utopia-cms 2020,2021. Aníbal Pacheco.
from django.core.management import BaseCommand
from django.core.cache import cache
from django.db import connection

from apps import core_articlevisits_mdb
from core.models import Article


class Command(BaseCommand):
    help = "Sync article views and reset view counters in cached table"

    def handle(self, *args, **options):
        vlevel = options.get('verbosity')
        aviews = core_articlevisits_mdb.posts.find({'views': {'$gt': 0}})
        updates = {}
        for av in aviews:
            try:
                article_id = av.get('article')
                if Article.objects.filter(id=article_id).exists():
                    updates[article_id] = av.get('views')
                    core_articlevisits_mdb.posts.update_one({'article': article_id}, {'$set': {'views': 0}})
                else:
                    # deleted article, remove the entry from mongo
                    if vlevel > 1:
                        print('removing deleted article %d from mongo' % article_id)
                    core_articlevisits_mdb.posts.delete_one({'article': article_id})
            except Exception as e:
                print(e)
        if updates:
            # build and exec update sql
            article_ids = ','.join(str(k) for k in updates.keys())
            update_query = "UPDATE %s SET views=views+ELT(FIELD(id,%s),%s) WHERE id IN (%s)" % (
                Article._meta.db_table,
                article_ids,
                ','.join(str(k) for k in updates.values()),
                article_ids,
            )
            try:
                with connection.cursor() as cursor:
                    cursor.execute(update_query)
            except Exception:
                print('ERROR updating views, update query: ' + update_query)
        # clear cache at the end
        cache.clear()
        if vlevel > 1:
            print('Sync completed.')
