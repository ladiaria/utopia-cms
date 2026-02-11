# coding=utf-8
from django.db.models import Max
from django.utils import timezone

from apps import mongo_db
from core.models import ArticleViewedBy


def latest_activity(user):
    """
    Latest activity is the most recent date between last article visited and last login.
    @returns datetime
    """
    if mongo_db is not None:
        latest_activity = list(
            mongo_db.core_articleviewedby.aggregate(
                [
                    {'$match': {'user': user.id}},
                    {'$group': {'_id': '$user', 'latest_activity': {'$max': '$viewed_at'}}},
                ]
            )
        )
        if latest_activity:
            latest_activity = timezone.localtime(
                timezone.make_aware(latest_activity[0]['latest_activity'].replace(microsecond=0), timezone.utc)
            )
    else:
        latest_activity = None

    if not latest_activity:
        latest_activity = ArticleViewedBy.objects.filter(user=user).aggregate(Max('viewed_at'))['viewed_at__max']

    to_compare = max(user.last_login, user.date_joined) if user.last_login else user.date_joined
    if hasattr(user, "subscriber"):
        to_compare = max(to_compare, user.subscriber.date_created)
    return max(latest_activity, to_compare) if latest_activity else to_compare
