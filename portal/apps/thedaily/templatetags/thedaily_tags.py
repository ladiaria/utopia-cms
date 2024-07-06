# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from future.utils import raise_

from datetime import timedelta
import locale

from django.conf import settings
from django.template import Library, Node, NodeList, TemplateSyntaxError, Variable
from django.contrib.contenttypes.models import ContentType
from django.contrib.flatpages.models import FlatPage
from django.utils import timezone

from core.models import Article
from thedaily.models import SubscriptionPrices


register = Library()

OPERATIONS = {
    'lt': lambda x, y: x < y,
    'lte': lambda x, y: x <= y,
    'eq': lambda x, y: x == y,
    'gte': lambda x, y: x >= y,
    'gt': lambda x, y: x > y,
}
UNITS = {
    's': 'seconds',
    'm': 'minutes',
    'h': 'hours',
    'd': 'days',
}


class TimeNode(Node):
    def __init__(self, nodelist_true, nodelist_false, future, time, operator, elapsed, unit):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.time = Variable(time)
        self.delta = self._get_delta(elapsed, unit)
        self.compare = OPERATIONS[operator]
        self.future = future

    def _get_delta(self, elapsed, unit):
        unit = UNITS[unit]
        return timedelta(**{unit: elapsed})

    def render(self, context):
        time = self.time.resolve(context)
        if self.future:
            in_range = self.compare(time, timezone.now() + self.delta)
        else:
            in_range = self.compare(timezone.now() - self.delta, time)
        if in_range:
            return self.nodelist_true.render(context)
        else:
            return self.nodelist_false.render(context)


@register.filter(name='count_following')
def count_following(user):
    return user.follow_set.filter(content_type=ContentType.objects.get_for_model(Article)).count()


@register.filter(name='has_restricted_access')
def has_restricted_access(user, article):
    """
    @pre: The article is restricted or is full restricted
    """
    return (
        hasattr(user, 'subscriber')
        and (
            user.subscriber.is_subscriber(article.main_section.edition.publication.slug)
            or article.full_restricted
            and user.subscriber.is_subscriber_any()
        )
    )


def if_time(parser, token):
    bits = list(token.split_contents())
    tag_name = bits[0]
    if tag_name.endswith('since'):
        future = False
    elif tag_name.endswith('until'):
        future = True
    if len(bits) != 4:
        raise_(TemplateSyntaxError, "%r takes three arguments" % tag_name)
    end_tag = 'end' + tag_name
    nodelist_true = parser.parse(('else', end_tag))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    parser.delete_first_token()
    try:
        time_int, time_unit = int(bits[3][:-1]), bits[3][-1]
    except ValueError:
        raise_(TemplateSyntaxError, "Invalid argument '%s'" % bits[3])
    if time_unit not in 'smhd':
        raise_(TemplateSyntaxError, "Invalid argument '%s'" % bits[3])
    return TimeNode(
        nodelist_true, nodelist_false, future=future, time=bits[1], operator=bits[2], elapsed=time_int, unit=time_unit
    )


register.tag('iftimesince', if_time)
register.tag('iftimeuntil', if_time)


@register.simple_tag
def subscriptionprice(subscription_type):
    try:
        price = SubscriptionPrices.objects.get(subscription_type=subscription_type).price
    except SubscriptionPrices.DoesNotExist:
        return ''
    else:
        locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)
        return f'{int(price):n}'


@register.simple_tag
def terms_and_conditions():
    fp_id = settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID
    if fp_id:
        try:
            return FlatPage.objects.get(id=fp_id).content
        except FlatPage.DoesNotExist:
            return ''
    else:
        return ''


@register.simple_tag
def nlsubscribed(user, nlobj, nltype=None):
    nl_type = getattr(nlobj, "nltype", nltype)
    return (
        (nl_type == "p" and nlobj in user.subscriber.newsletters.all())
        or (nl_type == "c" and nlobj in user.subscriber.category_newsletters.all())
    )


@register.filter(name='hasreplies')
def comment_has_replies(value):
    return value.last_child is not None
