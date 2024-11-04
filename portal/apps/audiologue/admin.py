# -*- coding: utf-8 -*-

from audiologue.models import Audio

from django.contrib.admin import ModelAdmin, site


class AudioAdmin(ModelAdmin):
    list_display = ("id", "date_uploaded", "title", "caption", "is_public")
    list_filter = ("is_public",)
    date_hierarchy = "date_uploaded"


site.register(Audio, AudioAdmin)
