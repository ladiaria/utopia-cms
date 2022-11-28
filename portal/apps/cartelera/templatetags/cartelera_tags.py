from __future__ import unicode_literals

from django import template
from django.template.loader import render_to_string

from cartelera.forms import RatingForm

register = template.Library()


@register.simple_tag(takes_context=True)
def rating(context, object):
    form = RatingForm(object, auto_id=False)
    return render_to_string('cartelera/rating.html', {'form': form}, context)
