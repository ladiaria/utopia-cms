# -*- coding: utf-8 -*-
# utopia-cms 2020. Aníbal Pacheco.
import pymongo

from django.core.management import BaseCommand
from django.core.cache import cache

from apps import core_articlevisits_mdb
from core.models import Article


class Command(BaseCommand):
    help = """Sync article views and reset view counters in cached table"""

    def handle(self, *args, **options):
        vlevel = options.get('verbosity')
        query = {'views': {'$gt': 0}}
        aviews = core_articlevisits_mdb.posts.find(query)
        aviews_count = core_articlevisits_mdb.posts.count_documents(query)
        # clear cache at the begginig
        cache.clear()
        for i, av in enumerate(aviews.sort('views', pymongo.DESCENDING), 1):
            try:
                article_id = av.get('article')
                article = Article.objects.get(id=article_id)
                article.views += av.get('views')
                core_articlevisits_mdb.posts.update_one({'article': article_id}, {'$set': {'views': 0}})
                if vlevel > u'1':
                    print('saving article %d (%d of %d)' % (article_id, i, aviews_count))
                article.save()
                if i > 30:
                    # also clear cache after first 30 updates
                    cache.clear()
            except Article.DoesNotExist:
                # deleted article, remove the entry from mongo
                if vlevel > u'1':
                    print('removing deleted article %d from mongo' % article_id)
                core_articlevisits_mdb.posts.delete_one({'article': article_id})
            except Exception as e:
                print(e)
        # clear cache at the end
        cache.clear()
