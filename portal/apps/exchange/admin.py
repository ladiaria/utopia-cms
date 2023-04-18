# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from exchange.models import Currency, Exchange
from django.contrib import admin


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'symbol', 'flag')


@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('currency', 'date', 'buy', 'sale')
    list_filter = ('currency', 'date')
    date_hierarchy = 'date'


# admin registers
