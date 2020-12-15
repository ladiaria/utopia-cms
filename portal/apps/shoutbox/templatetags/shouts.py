# -*- coding: utf-8 -*-
from shoutbox.models import get_last_shouts

from django.template import Library, Node
from django.template.loader import get_template

from os.path import join

register = Library()
templates = 'shoutbox/templates/'


class ScriptsNode(Node):
    def render(self, context):
        scripts_template = get_template(join(templates, 'scripts.html'))
        return scripts_template.render(context)


class BoxNode(Node):
    def render(self, context):
        box_template = get_template(join(templates, 'box.html'))
        context.update({'shouts': get_last_shouts()})
        return box_template.render(context)


@register.tag('load_shout_scripts')
def scripts(parser, token):
    # bits = token.contents.split()
    return ScriptsNode()

@register.tag('render_box')
def box(parser, token):
    # bits = token.contents.split()
    return BoxNode()
