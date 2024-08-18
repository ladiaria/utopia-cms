# -*- coding: utf-8 -*-
from django.template import Library

register = Library()


class SpacelessNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        from libs.utils import spaceless

        return spaceless(self.nodelist.render(context).strip())


@register.tag
def spaceless(parser, token):
    nodelist = parser.parse(('endspaceless',))
    parser.delete_first_token()
    return SpacelessNode(nodelist)
