# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin, site
from models import TagGroup


class TagGroupAdmin(ModelAdmin):
    list_display = ('slug', 'tags_names')


site.register(TagGroup, TagGroupAdmin)
