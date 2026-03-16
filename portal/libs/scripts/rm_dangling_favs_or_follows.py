from favit.models import Favorite
from actstream.models import Follow

from django.db.models.deletion import Collector


def run(*args, **kwargs):
    fav_to_delete, follow_to_delete = [], []
    for fav in Favorite.objects.iterator():
        if fav.target is None:
            fav_to_delete.append(fav)
    for follow in Follow.objects.iterator():
        if follow.follow_object is None:
            follow_to_delete.append(follow)
    if fav_to_delete or follow_to_delete:
        collector = Collector(using='default')
        collector.collect(fav_to_delete)
        collector.collect(follow_to_delete)
        if any(k not in (Favorite, Follow) for k in collector.data.keys()):
            print("Error: some objects are not Favorite or Follow")
            return
        collector.delete()
