# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin, site

from .models import Audio


class AudioAdmin(ModelAdmin):
    list_display = ("id", "date_uploaded", "title", "caption", "is_public")
    list_filter = ("is_public",)
    date_hierarchy = "date_uploaded"


site.register(Audio, AudioAdmin)
