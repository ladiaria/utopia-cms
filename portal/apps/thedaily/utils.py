# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from operator import attrgetter

from actstream.models import Follow
from actstream.registry import check
from social_django.models import UserSocialAuth

from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Value
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from core.models import Category, Publication, ArticleViewedBy
from thedaily.models import Subscriber, SentMail, OAuthState
from dashboard.models import AudioStatistics

from .models import Subscriber


non_relevant_data_max_ammounts = {
    User: 1,
    Subscriber: 1,
    Subscriber.newsletters.through: 10,
    Subscriber.category_newsletters.through: 10,
    UserSocialAuth: 1,
    SentMail: 10,
    ArticleViewedBy: 10,
    OAuthState: 1,
    AudioStatistics: 10,
    Follow: 10,
}


def collector_analysis(collector_data, indent_level=1):
    data_keys = set(collector_data.keys())
    safety, report = True, ""
    for key in collector_data:
        key_count = len(collector_data[key])
        if key not in non_relevant_data_max_ammounts or key_count > non_relevant_data_max_ammounts[key]:
            safety = False
        report += "\n%s%s: %d" % ("\t" * indent_level, key, key_count)
    return safety, report


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


def get_all_newsletters():
    return list(Publication.objects.filter(has_newsletter=True)) + list(Category.objects.filter(has_newsletter=True))


def get_profile_newsletters_ordered():
    custom_order = getattr(settings, 'THEDAILY_EDIT_PROFILE_NEWSLETTERS_CUSTOM_ORDER', ())
    publications = list(Publication.objects.filter(has_newsletter=True).annotate(nltype=Value('p')))
    categories = list(Category.objects.filter(has_newsletter=True).annotate(nltype=Value('c')))
    nl_unsorted = publications + categories
    nl_custom_ordered = [next((x for x in nl_unsorted if x.slug == o), None) for o in custom_order]
    nl_alpha = [nl_obj for nl_obj in nl_unsorted if nl_obj not in nl_custom_ordered]
    nl_alpha.sort(key=attrgetter("slug"))
    return [nl_obj for nl_obj in nl_custom_ordered if nl_obj] + nl_alpha
