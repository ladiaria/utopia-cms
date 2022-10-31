# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from actstream.models import Follow
from actstream.registry import check

from core.models import Category
from thedaily.models import Subscriber


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


def subscribers_nl_iter(receivers, starting_from_s, starting_from_ns):
    """
    iterate over a receivers QS and yield the subscribers first, saving the
    not subscribers ids in a temporal list an then yield them also after.
    """
    receivers2 = []
    for s in receivers.distinct().order_by('user__email').iterator():
        try:
            if s.user.email:
                # validate email before doing anything
                try:
                    validate_email(s.user.email)
                except ValidationError:
                    continue
                if s.is_subscriber():
                    if not starting_from_s or (starting_from_s and s.user.email > starting_from_s):
                        yield s, True
                else:
                    if not starting_from_ns or (starting_from_ns and s.user.email > starting_from_ns):
                        receivers2.append(s.id)
        except Exception:
            # rare but possible (for example, a subscriber with no user)
            continue
    for sus_id in receivers2:
        try:
            yield Subscriber.objects.get(id=sus_id), False
        except Subscriber.DoesNotExist:
            # rare, but could be recently deleted
            continue


def subscribers_nl_iter_filter(iter, filter_func):
    for item in iter:
        if filter_func(item):
            yield item
