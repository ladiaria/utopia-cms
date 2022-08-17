# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from videologue.models import YouTubeVideo

from django.template import (Context, Library, loader, Node, TemplateSyntaxError)


register = Library()
TPL_DIR = 'videologue/templates/'


class RenderLatestVideoNode(Node):
    def __init__(self, kwcontext):
        self.kw = kwcontext

    def render(self, context):
        try:
            video = YouTubeVideo.objects.latest()
        except:
            video = None
        context.update({self.kw: video})
        return ''


class RenderVideoNode(Node):
    def __init__(self, kwcontext, vid):
        self.kw = kwcontext
        self.vid = vid

    def render(self, context):
        try:
            video = YouTubeVideo.objects.get(id=self.vid)
        except:
            video = None
        context.update({self.kw: video})
        return ''


@register.tag
def get_latest_video(parser, token):
    """Usage: {% get_latest_video as video_object %}"""

    bits = token.contents.split()
    if len(bits) != 3 or bits[1] != 'as':
        raise TemplateSyntaxError('Invalid arguments for %s' % bits[0])
    return RenderLatestVideoNode(bits[2])

@register.tag
def get_video(parser, token):
    """Usage: {% get_video id as video_object %}"""

    bits = token.contents.split()
    if len(bits) != 4 or bits[2] != 'as':
        raise TemplateSyntaxError('Invalid arguments for %s' % bits[0])
    return RenderVideoNode(bits[3], bits[1])

@register.filter
def render_video(video):
    if not video:
        return ''
    tpl = loader.get_template(
        TPL_DIR + '%s/module.html' % video.__class__.__name__.lower())
    return tpl.render({'video': video})
