from __future__ import absolute_import
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from .models import Pelicula, ObraTeatro, Evento, Cine, CategoriaEvento, LiveEmbedEvent, ArchivedEvent


@never_cache
@staff_member_required
def index(request):
    secciones = CategoriaEvento.objects.order_by('order')
    return render(request, 'cartelera/index.html', {'secciones': secciones})


@never_cache
@staff_member_required
def cine(request, slug):
    cine = get_object_or_404(Cine, slug=slug)
    return render(request, 'cartelera/cine.html', {'cine': cine})


@never_cache
@staff_member_required
def pelicula(request, slug):
    pelicula = get_object_or_404(Pelicula, slug=slug)
    return render(request, 'cartelera/pelicula.html', {'pelicula': pelicula})


@never_cache
@staff_member_required
def obrateatro(request, slug):
    obrateatro = get_object_or_404(ObraTeatro, slug=slug)
    return render(request, 'cartelera/obrateatro.html', {'obrateatro': obrateatro})


@never_cache
@staff_member_required
def evento(request, slug):
    """
    TODO: This app is very old, has broken parts, should be fixed and merged with the app "comunidad" (both have
          similar purposes). Only the next "vivo" features are new.
          For example, here in this view, we had to treat the "evento" as a "pelicula" because we don't know why the
          evento.html template is missing.
    """
    evento = get_object_or_404(Evento, slug=slug)
    return render(request, 'cartelera/pelicula.html', {'pelicula': evento})


@never_cache
def vivo(request, archived_event_id=None):
    context = {
        'logo_template': getattr(settings, 'CARTELERA_EVENTS_LOGO_TEMPLATE', None),
        'resume_template': getattr(settings, 'CARTELERA_EVENTS_RESUME_TEMPLATE', 'core/templates/edition/resume.html')}
    if archived_event_id:
        context.update({'event': get_object_or_404(ArchivedEvent, id=archived_event_id), 'is_detail': True})
        return render(request, 'cartelera/vivo_archive.html', context)
    try:
        active_event = LiveEmbedEvent.objects.get(active=True)
    except LiveEmbedEvent.DoesNotExist:
        active_event = None
    context.update({'event': active_event, 'is_detail': True})
    return render(request, 'cartelera/vivo.html', context)


@never_cache
def notification_closed(request, live_embed_event_id):
    closed = request.session.get(
        'live_embed_events_notifications_closed', set())
    closed.add(int(live_embed_event_id))
    request.session['live_embed_events_notifications_closed'] = closed
    return HttpResponse()


@never_cache
@staff_member_required
def categoria(request, slug):
    categoria = get_object_or_404(CategoriaEvento, slug=slug)
    return render(request, 'cartelera/categoria.html',
                  {'categoria': categoria})
