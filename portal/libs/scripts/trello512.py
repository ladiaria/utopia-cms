from apps import core_articleviewedby_mdb
from core.models import Article

for pid in Article.objects.filter(public=True).values_list('id', flat=True):
    core_articleviewedby_mdb.posts.update_many(
        {'article': pid}, {'$set': {'public': True}})
