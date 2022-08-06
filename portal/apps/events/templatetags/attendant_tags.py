# # -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.template import Node, Library, Variable, VariableDoesNotExist
from django.template.loader import render_to_string

from events.forms import AttendantFormRender

register = Library()


class AttendantFormNode(Node):
    def __init__(self, activity_id):
        self.activity_id = Variable(activity_id)

    def render(self, context):
        try:
            return render_to_string(
                'attendant_form.html',
                {'form': AttendantFormRender(), 'activity_id': self.activity_id.resolve(context)},
            )
        except VariableDoesNotExist:
            return ''


@register.tag
def attendant_form(parser, token):
    tag_name, activity_id = token.split_contents()
    return AttendantFormNode(activity_id)
