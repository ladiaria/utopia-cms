# -*- coding: utf-8 -*-
from audiologue.models import Audio

from django.contrib.admin import ModelAdmin, site

class AudioAdmin(ModelAdmin):
    pass

site.register(Audio, AudioAdmin)
