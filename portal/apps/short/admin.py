# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin, site
from models import Url

class UrlAdmin(ModelAdmin):
    list_display = ('url', 'surl')
    search_field = ('url', )

site.register(Url, UrlAdmin)
