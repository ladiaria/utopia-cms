from django.conf import settings
from djangoratings.views import AddRatingView

from django.http import HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext

from models import Pelicula, ObraTeatro, Evento, Cine, CategoriaEvento, LiveEmbedEvent, ArchivedEvent


@never_cache
@staff_member_required
def index(request):
    secciones = CategoriaEvento.objects.order_by('order')
    return render_to_response(
        'cartelera/index.html', {'secciones': secciones},
        context_instance=RequestContext(request))


@never_cache
@staff_member_required
def cine(request, slug):
    cine = get_object_or_404(Cine, slug=slug)
    return render_to_response(
        'cartelera/cine.html', {'cine': cine},
        context_instance=RequestContext(request))


@never_cache
@staff_member_required
def pelicula(request, slug):
    pelicula = get_object_or_404(Pelicula, slug=slug)
    return render_to_response(
        'cartelera/pelicula.html', {'pelicula': pelicula},
        context_instance=RequestContext(request))


@never_cache
@staff_member_required
def obrateatro(request, slug):
    obrateatro = get_object_or_404(ObraTeatro, slug=slug)
    return render_to_response(
        'cartelera/obrateatro.html', {'obrateatro': obrateatro},
        context_instance=RequestContext(request))


@never_cache
@staff_member_required
def evento(request, slug):
    evento = get_object_or_404(Evento, slug=slug)
    return render_to_response(
        'cartelera/evento.html', {'evento': evento},
        context_instance=RequestContext(request))


@never_cache
def vivo(request, archived_event_id=None):
    context = {
        'logo_template': getattr(settings, 'CARTELERA_EVENTS_LOGO_TEMPLATE', None),
        'resume_template': getattr(settings, 'CARTELERA_EVENTS_RESUME_TEMPLATE', 'core/templates/edition/resume.html')}
    if archived_event_id:
        context.update({
            'event': get_object_or_404(ArchivedEvent, id=archived_event_id), 'is_detail': True,
            'archive_external_url': getattr(settings, 'CARTELERA_ARCHIVE_EXTERNAL_URL', '#')})
        return render_to_response('cartelera/vivo_archive.html', context, context_instance=RequestContext(request))
    try:
        active_event = LiveEmbedEvent.objects.get(active=True)
    except LiveEmbedEvent.DoesNotExist:
        active_event = None
    context.update({
        'event': active_event, 'is_detail': True,
        'events_external_url': getattr(settings, 'CARTELERA_EVENTS_EXTERNAL_URL', '#')})
    return render_to_response('cartelera/vivo.html', context, context_instance=RequestContext(request))


@never_cache
def notification_closed(request, live_embed_event_id):
    closed = request.session.get(
        'live_embed_events_notifications_closed', set())
    closed.add(int(live_embed_event_id))
    request.session['live_embed_events_notifications_closed'] = closed
    return HttpResponse()


@never_cache
@staff_member_required
def rating(request):
    content_type_id = request.POST['content_type_id']
    object_id = request.POST['object_id']
    params = {
        'content_type_id': content_type_id,
        'object_id': object_id,
        'field_name': 'rating',
        'score': request.POST['rating'],
    }
    response = AddRatingView()(request, **params)
    if response.status_code == 200:
        ct = ContentType.objects.get_for_id(content_type_id)
        obj = ct.get_object_for_this_type(pk=object_id)
        return HttpResponse(
            obj.rating.get_rating(), mimetype="application/json")
    return HttpResponse(status=response.status_code)


@never_cache
@staff_member_required
def categoria(request, slug):
    categoria = get_object_or_404(CategoriaEvento, slug=slug)
    return render_to_response(
        'cartelera/categoria.html', {'categoria': categoria},
        context_instance=RequestContext(request))
