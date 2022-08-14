# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from audiologue.models import Audio

from django.contrib.admin import ModelAdmin, site

class AudioAdmin(ModelAdmin):
    pass

site.register(Audio, AudioAdmin)
