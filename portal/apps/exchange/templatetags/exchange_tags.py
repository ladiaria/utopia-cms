# -*- coding: utf-8 -*-
from past.utils import old_div
from exchange.models import Exchange, Currency

from django.template import Library, loader


register = Library()


@register.simple_tag
def exchange_table():
    try:
        date = Exchange.objects.latest().date
    except Exception:
        return ''
    exchange_list = Exchange.objects.filter(date=date)
    return loader.render_to_string('exchange/templates/detail.html', {'exchange_list': exchange_list, 'date': date})


@register.filter
def to_usd(value):
    """ Filter to convert to USD """
    try:
        usd = Currency.objects.get(slug='dolar')
        return '%.2f %s' % (round(old_div(value, Exchange.objects.filter(currency=usd).latest().buy), 2), usd.symbol)
    except Exception:
        return ''


@register.filter
def to_usd_val(value):
    """
    Filter to convert to USD no suffix, if the value is not float you can use:
    {{ value|floatformat|to_usd_val }}
    """
    try:
        usd = Currency.objects.get(slug='dolar')
        return '%.2f' % round(float(value) / Exchange.objects.filter(currency=usd).latest().buy, 2)
    except Exception:
        return ''
