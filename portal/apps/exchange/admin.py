# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from exchange.models import Currency, Exchange
from django.contrib import admin


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'symbol', 'flag')


class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('currency', 'date', 'buy', 'sale')
    list_filter = ('currency', 'date')
    date_hierarchy = 'date'


# admin registers
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Exchange, ExchangeAdmin)
