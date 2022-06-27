# coding=utf-8
from django.db.models import Max

from core.models import ArticleViewedBy

from apps import mongo_db


def latest_activity(user):
    """
    Latest activity is the most recent date between last article visited and last login.
    @returns datetime
    """
    if mongo_db:
        latest_activity = list(
            mongo_db.core_articleviewedby.aggregate(
                [
                    {'$match': {'user': user.id}},
                    {'$group': {'_id': '$user', 'latest_activity': {'$max': '$viewed_at'}}},
                ]
            )
        )
        if latest_activity:
            latest_activity = latest_activity[0]['latest_activity']
    else:
        latest_activity = None

    if not latest_activity:
        latest_activity = ArticleViewedBy.objects.filter(user=user).aggregate(Max('viewed_at'))['viewed_at__max']

    # Sometimes user.date_joined > user.last_login but only for 1 or 2 seconds, using last_login is good enough.
    return max(latest_activity, user.last_login) if latest_activity else user.last_login
