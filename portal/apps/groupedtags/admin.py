# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.contrib.admin import ModelAdmin, site
from .models import TagGroup


class TagGroupAdmin(ModelAdmin):
    list_display = ('slug', 'tags_names')


site.register(TagGroup, TagGroupAdmin)
