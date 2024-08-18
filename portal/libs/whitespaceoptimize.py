# -*- coding: utf-8 -*-
from future.utils import raise_

from slimmer import guessSyntax, css_slimmer, html_slimmer, js_slimmer

from django import template


class WhitespaceOptimizeNode(template.Node):
    def __init__(self, nodelist, format=None):
        self.nodelist = nodelist
        self.format = format

    def render(self, context):
        code = self.nodelist.render(context)
        if self.format == 'css':
            return css_slimmer(code)
        elif self.format in ('js', 'javascript'):
            return js_slimmer(code)
        elif self.format == 'html':
            return html_slimmer(code)
        else:
            format = guessSyntax(code)
            if format:
                self.format = format
                return self.render(context)

        return code


register = template.Library()


@register.tag(name='whitespaceoptimize')
def do_whitespaceoptimize(parser, token):
    nodelist = parser.parse(('endwhitespaceoptimize',))
    parser.delete_first_token()

    _split = token.split_contents()
    format = ''
    if len(_split) > 1:
        tag_name, format = _split
        if not (format[0] == format[-1] and format[0] in ('"', "'")):
            raise_(template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name)

    return WhitespaceOptimizeNode(nodelist, format[1:-1])
