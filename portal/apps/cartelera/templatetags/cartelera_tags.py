from __future__ import unicode_literals

from django import template
from django.template.loader import render_to_string

from cartelera.models import LiveEmbedEvent
from cartelera.forms import RatingForm

register = template.Library()


@register.simple_tag(takes_context=True)
def rating(context, object):
    form = RatingForm(object, auto_id=False)
    return render_to_string('cartelera/rating.html', {'form': form}, context)


@register.simple_tag(takes_context=True)
def render_live_embed_event_notification(context):
    try:
        event = LiveEmbedEvent.objects.get(active=True, notification=True)
        if event.id not in context['request'].session.get('live_embed_events_notifications_closed', set()):
            return render_to_string('cartelera/live_embed_event_notification.html', {'event': event})
    except (LiveEmbedEvent.DoesNotExist, LiveEmbedEvent.MultipleObjectsReturned):
        pass
    return ''
