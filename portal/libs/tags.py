# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from libs.utils import remove_spaces

from django.template import Library

register = Library()


class SpacelessNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        s = self.nodelist.render(context).strip()
        return remove_spaces(s)


@register.tag
def spaceless(parser, token):
    nodelist = parser.parse(('endspaceless',))
    parser.delete_first_token()
    return SpacelessNode(nodelist)
