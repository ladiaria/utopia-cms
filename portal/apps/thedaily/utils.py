# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from actstream.models import Follow
from actstream.registry import check

from core.models import Category


def recent_following(user, *models):
    """ The same as actstream.managers.FollowManager.following but sorted by '-started' """
    qs = Follow.objects.filter(user=user)
    for model in models:
        check(model)
        qs = qs.filter(content_type=ContentType.objects.get_for_model(model))
    return [follow.follow_object for follow in qs.fetch_generic_relations('follow_object').order_by('-started')]


def add_default_category_newsletters(subscriber):
    default_category_nls = settings.THEDAILY_DEFAULT_CATEGORY_NEWSLETTERS
    for default_category_slug in default_category_nls:
        try:
            category = Category.objects.get(slug=default_category_slug)
            if category.has_newsletter:
                subscriber.category_newsletters.add(category)
        except Category.DoesNotExist:
            pass
