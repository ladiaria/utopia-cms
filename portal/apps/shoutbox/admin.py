# -*- coding: utf-8 -*-
from shoutbox.models import Shout

from django.contrib.admin import site, ModelAdmin


class ShoutModelAdmin(ModelAdmin):
    list_display = ('message', 'user', 'post_date')
    search_fields = ('message',)

site.register(Shout, ShoutModelAdmin)
