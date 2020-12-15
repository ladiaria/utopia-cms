# -*- coding: utf-8 -*-
# la diaria 2019,2020. Aníbal Pacheco.
import pymongo

from django.core.management import BaseCommand
from django.core.cache import cache

from apps import core_articlevisits_mdb
from core.models import Article


class Command(BaseCommand):
    help = """Sync article views and reset view counters in cached table"""

    def handle(self, *args, **options):
        vlevel = options.get('verbosity')
        aviews = core_articlevisits_mdb.posts.find({'views': {'$gt': 0}})
        aviews_count = aviews.count()
        # clear cache at the begginig
        cache.clear()
        for i, av in enumerate(aviews.sort('views', pymongo.DESCENDING), 1):
            try:
                article_id = av.get('article')
                article = Article.objects.get(id=article_id)
                article.views += av.get('views')
                core_articlevisits_mdb.posts.update_one(
                    {'article': article_id}, {'$set': {'views': 0}})
                if vlevel > u'1':
                    print('saving article %d of %d' % (i, aviews_count))
                article.save()
                if i > 30:
                    # also clear cache after first 30 updates
                    cache.clear()
            except Exception as e:
                print(e.message)
