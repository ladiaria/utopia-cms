# -*- coding: utf-8 -*-
from videologue.models import Video, YouTubeVideo
from videologue.forms import YouTubeVideoForm

from django.contrib.admin import ModelAdmin, site


class VideoAdmin(ModelAdmin):
    pass


class YouTubeVideoAdmin(ModelAdmin):
    list_display = ('title', 'url', 'date_created', "yt_id")
    form = YouTubeVideoForm
    exclude = ('yt_id', )


site.register(Video, VideoAdmin)
site.register(YouTubeVideo, YouTubeVideoAdmin)
