# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.forms import ModelForm
from django.contrib.admin import ModelAdmin, site
from django.contrib.admin.widgets import FilteredSelectMultiple

from .models import TagGroup


class TagGroupAdminForm(ModelForm):

    class Meta:
        model = TagGroup
        fields = "__all__"
        widgets = {"tags": FilteredSelectMultiple("tags", False)}


class TagGroupAdmin(ModelAdmin):
    form = TagGroupAdminForm
    list_display = ('slug', 'tags_names')


site.register(TagGroup, TagGroupAdmin)
