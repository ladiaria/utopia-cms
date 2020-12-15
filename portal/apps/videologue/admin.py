# -*- coding: utf-8 -*-
from videologue.models import Video, YouTubeVideo
from videologue.forms import YouTubeVideoForm

from django.contrib.admin import ModelAdmin, site


class VideoAdmin(ModelAdmin):
    pass


class YouTubeVideoAdmin(ModelAdmin):
    form = YouTubeVideoForm
    exclude = ('yt_id', )


site.register(Video, VideoAdmin)
site.register(YouTubeVideo, YouTubeVideoAdmin)
