# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.template import Node, Library, Variable, TemplateSyntaxError
from django.utils.timezone import now

from ..models import Event


register = Library()


class EventCountNode(Node):
    def __init__(self, day, keyword):
        self.day = Variable(day)
        self.keyword = keyword

    def render(self, context):
        day = self.day.resolve(context)
        params = {'date__year': day.year, 'date__month': day.month, 'date__day': day.day}
        context.update({self.keyword: Event.objects.filter(**params).count()})
        return ''


@register.tag
def get_event_count(parser, token):
    """Usage: {% get_event_count on day as event_count %}"""

    bits = token.contents.split()
    if len(bits) != 5 or bits[1] != 'on' or bits[3] != 'as':
        raise TemplateSyntaxError('Invalid arguments for %s' % bits[0])
    day = bits[2]
    keyword = bits[4]
    return EventCountNode(day, keyword)


class LatestEventsNode(Node):
    def __init__(self, how_many, keyword):
        self.how_many = how_many
        self.keyword = keyword

    def render(self, context):
        events = Event.objects.filter(date__gte=now().date())[:self.how_many]
        context.update({self.keyword: events})
        return ''


@register.tag
def get_latest_events(parser, token):
    """ Usage: {% get_latest_events "10" as event_list %} """

    bits = token.contents.split()
    if len(bits) != 4 or bits[2] != 'as':
        raise TemplateSyntaxError('Invalid arguments for %s' % bits[0])
    try:
        how_many = int(bits[1].strip('"'))
    except ValueError:
        raise TemplateSyntaxError('Invalid arguments for %s' % bits[0])
    return LatestEventsNode(how_many, bits[3])
