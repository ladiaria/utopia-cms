from apps import mongo_db
from core.models import Article

for pid in Article.objects.filter(public=True).values_list('id', flat=True):
    mongo_db.core_articleviewedby.update_many(
        {'article': pid}, {'$set': {'public': True}})
