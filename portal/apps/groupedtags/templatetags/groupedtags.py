# -*- coding: utf-8 -*-
from django.template import Library, loader

from ..models import TagGroup


register = Library()


@register.simple_tag(takes_context=True)
def render_tag_group(context, group_slug):
    try:
        context['tg'] = TagGroup.objects.get(slug=group_slug)
    except TagGroup.DoesNotExist:
        return u''
    else:
        return loader.render_to_string('groupedtags/templates/tag_cards.html', context.flatten())
