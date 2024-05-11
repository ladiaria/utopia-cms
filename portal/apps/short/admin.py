# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.admin import ModelAdmin, site

from .models import Url as ShortUrl


class ShortUrlAdmin(ModelAdmin):
    list_display = ('url_formatted', 'surl')
    search_field = ('url',)


site.register(ShortUrl, ShortUrlAdmin)
