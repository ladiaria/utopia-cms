# -*- coding: utf-8 -*-
from django.template import Library, Node, NodeList, TemplateSyntaxError, \
    Variable
from actstream.models import following
from core.models import Article
from datetime import date, datetime, timedelta

register = Library()

OPERATIONS = {
    'lt': lambda x,y: x < y,
    'lte': lambda x,y: x <= y,
    'eq': lambda x,y: x == y,
    'gte': lambda x,y: x >= y,
    'gt': lambda x,y: x > y,
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
            in_range = self.compare(time, datetime.now() + self.delta)
        else:
            in_range = self.compare(datetime.now() - self.delta, time)
        if in_range:
            return self.nodelist_true.render(context)
        else:
            return self.nodelist_false.render(context)


@register.filter(name='count_following')
def count_following(user):
    return len(following(user))


def if_time(parser, token):
    bits = list(token.split_contents())
    tag_name = bits[0]
    if tag_name.endswith('since'):
        future = False
    elif tag_name.endswith('until'):
        future = True
    if len(bits) != 4:
        raise TemplateSyntaxError, "%r takes three arguments" % tag_name
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
        raise TemplateSyntaxError, "Invalid argument '%s'" % bits[3]
    if time_unit not in 'smhd':
        raise TemplateSyntaxError, "Invalid argument '%s'" % bits[3]
    return TimeNode(nodelist_true, nodelist_false, future=future, time=bits[1],
        operator=bits[2], elapsed=time_int, unit=time_unit)


register.tag('iftimesince', if_time)
register.tag('iftimeuntil', if_time)


# filters
@register.filter(name='hasreplies')
def comment_has_replies(value):
    return value.last_child is not None
