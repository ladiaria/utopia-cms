# -*- coding: utf-8 -*-

from os.path import join
import random as rdm
import json
from operator import attrgetter
from urllib.parse import urlencode
from pydoc import locate
import requests

from actstream.models import Follow
from actstream.registry import check
from favit.models import Favorite
from social_django.models import UserSocialAuth
from django_amp_readerid.models import UserReaderId

from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Value
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.template import Engine
from django.template.exceptions import TemplateDoesNotExist

from core.models import Category, Publication, ArticleViewedBy, DeviceSubscribed
from dashboard.models import AudioStatistics
from .models import Subscriber, SentMail, OAuthState, SubscriberEvent, MailtrainList


non_relevant_data_max_amounts = {
    User: 1,
    Subscriber: 1,
    SubscriberEvent: 1,
    Subscriber.newsletters.through: 10,
    Subscriber.category_newsletters.through: 10,
    UserSocialAuth: 1,
    SentMail: 10,
    ArticleViewedBy: 10,
    DeviceSubscribed: 10,
    OAuthState: 1,
    AudioStatistics: 10,
    Follow: 10,
    Favorite: 10,
    User.user_permissions.through: 3,
    UserReaderId: 2,
}
extra_func = locate(getattr(settings, "THEDAILY_COLLECTOR_ANALYSIS_EXTRA_LIMITS", "None"))
if extra_func:
    non_relevant_data_max_amounts.update(extra_func())

movable = (
    SubscriberEvent,
    ArticleViewedBy,
    Subscriber.newsletters.through,
    Subscriber.category_newsletters.through,
    AudioStatistics,
    Follow,
    Favorite,
    User.user_permissions.through,
)


def collector_analysis(collector_data, indent_level=1, ignore_movable=False):
    safety, report = True, ""
    for key in collector_data:
        key_count = len(collector_data[key])
        if key not in non_relevant_data_max_amounts or key_count > non_relevant_data_max_amounts[key]:
            if not ignore_movable or key not in movable:
                safety = False
        report += "\n%s%s: %d" % ("\t" * indent_level, key, key_count)
    return safety, report


def move_data(s0, s1):
    # copies "movable" data from subscriber s0 to subscriber s1
    for avb in ArticleViewedBy.objects.filter(user=s0.user):
        try:
            ArticleViewedBy.objects.filter(id=avb.id).update(user=s1.user)
        except IntegrityError:
            pass
    for uperm in User.user_permissions.through.objects.filter(user=s0.user):
        try:
            User.user_permissions.through.objects.filter(id=uperm.id).update(user=s1.user)
        except IntegrityError:
            pass
    Follow.objects.filter(user=s0.user).update(user=s1.user)
    Favorite.objects.filter(user=s0.user).update(user=s1.user)
    SubscriberEvent.objects.filter(subscriber=s0).update(subscriber=s1)
    AudioStatistics.objects.filter(subscriber=s0).update(subscriber=s1)
    for p in s0.newsletters.all():
        s1.newsletters.add(p)
    for c in s0.category_newsletters.all():
        s1.category_newsletters.add(c)


def qparamstr(qparams):
    qparams_str = urlencode(qparams)
    return ('?%s' % qparams_str) if qparams_str else ''


def recent_following(user, *models):
    """ The same as actstream.managers.FollowManager.following but sorted by '-started' """
    qs = Follow.objects.filter(user=user)
    for model in models:
        check(model)
        qs = qs.filter(content_type=ContentType.objects.get_for_model(model))
    return [follow.follow_object for follow in qs.fetch_generic_relations('follow_object').order_by('-started')]


def add_default_mailtrain_lists(subscriber):
    # Mailtrain lists. TODO: this should be done with a new API to add the email to all "signup-default" lists
    api_uri, api_key = settings.CRM_API_BASE_URI, getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
    if api_uri and api_key:
        for mlist in MailtrainList.objects.filter(on_signup=True):
            try:
                requests.post(
                    api_uri + "mailtrain_list_subscription/",
                    headers={"Authorization": "Api-Key " + api_key},
                    data={"email": subscriber.user.email, "list_id": mlist.list_cid},
                )
            except Exception:
                pass


def add_default_newsletters(subscriber):
    default_category_nls = settings.THEDAILY_DEFAULT_CATEGORY_NEWSLETTERS
    for default_category_slug in default_category_nls:
        try:
            category = Category.objects.get(slug=default_category_slug)
            if category.has_newsletter:
                subscriber.category_newsletters.add(category)
        except Category.DoesNotExist:
            pass
    add_default_mailtrain_lists(subscriber)


def unsubscribed_newsletters(subscriber):
    """
    Get unsubscribed newsletters for subscriber supplied
    @params: subscriber instance
    @return: List of unsubscribed newsletters
    """
    publications = list(Publication.objects.filter(has_newsletter=True).annotate(nltype=Value('p')))
    categories = list(Category.objects.filter(has_newsletter=True).annotate(nltype=Value('c')))
    all_nl = publications + categories  # get newsletters for cards presentation format
    if subscriber:
        subscribed_nls = list(subscriber.newsletters.all()) + list(subscriber.category_newsletters.all())
        result_nl = list(set(all_nl) - set(subscribed_nls))
        rdm.shuffle(result_nl)
        return result_nl
    else:
        return all_nl


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


def google_phone_next_page(request, is_new):
    next_page = request.session.pop("next", None)  # allways pop next page from session
    # but gives precedence to: welcome page if is_new; next entry in get/post when not is_new
    return reverse('account-welcome') if is_new else (
        request.GET.get("next", request.POST.get("next_page")) or next_page
    )


def put_data_to_crm(api_url, data):
    """
    Performs an PUT request to the CRM app
    api_url is the request url and data is the request body data
    If there are missing data for do the request; return None
    @param api_url: target url in str format
    @param data: request body data
    """
    if getattr(settings, "CRM_SYNC_ENABLED", False):
        api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
        if all((settings.CRM_UPDATE_USER_ENABLED, api_url, api_key)):
            requests.put(api_url, headers={'Authorization': 'Api-Key ' + api_key}, data=data).raise_for_status()


def post_data_to_crm(api_url, data):
    """
    Performs an POST request to the CRM app
    api_url is the request url and data is the request body data
    If there are missing data for do the request; return None
    @param api_url: target url in str format
    @param data: request body data
    """
    if getattr(settings, "CRM_SYNC_ENABLED", False):
        api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
        if all((settings.CRM_UPDATE_USER_ENABLED, api_url, api_key)):
            requests.post(api_url, headers={'Authorization': 'Api-Key ' + api_key}, data=data).raise_for_status()


def delete_data_from_crm(api_url, data):
    """
    Performs an DELETE request to the CRM app
    api_url is the request url and data is the request body data
    If there are missing data for do the request; return None
    @param api_url: target url in str format
    @param data: request body data
    """
    if getattr(settings, "CRM_SYNC_ENABLED", False):
        api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
        if all((settings.CRM_UPDATE_USER_ENABLED, api_url, api_key)):
            payload = json.dumps(data)
            headers = {
                'Authorization': 'Api-Key ' + api_key,
                'Content-Type': 'application/json'
            }
            requests.delete(api_url, headers=headers, data=payload).raise_for_status()


def product_checkout_template(product_slug, steps=False):
    steps_suffix = "_steps" if steps else ""
    template, engine = f"thedaily/templates/market/product{steps_suffix}.html", Engine.get_default()
    custom_dir = getattr(settings, "THEDAILY_MARKET_PRODUCTS_TEMPLATE_DIR", None)
    if custom_dir:
        template_try = join(custom_dir, f"{product_slug}{steps_suffix}.html")
        try:
            engine.get_template(template_try)
        except TemplateDoesNotExist:
            pass
        else:
            template = template_try
    return template
