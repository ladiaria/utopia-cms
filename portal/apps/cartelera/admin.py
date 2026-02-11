# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin, TabularInline, site

from .models import (
    Cine,
    Pelicula,
    PeliculaEnCine,
    Teatro,
    ObraEnTeatro,
    ObraTeatro,
    CategoriaEvento,
    Evento,
    LiveEmbedEvent,
    ArchivedEvent,
)


class EventoBaseAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    exclude = ('categoria', 'type',)


class ArchivedEventAdmin(ModelAdmin):
    list_display = ('id', 'title', 'access_type', 'link')
    list_editable = ('title', 'access_type', )
    list_filter = ('access_type', )
    readonly_fields = ('link', )
    fieldsets = (
        (u'Link', {'fields': ('link', )}),
        (u'Configuración', {'fields': ('access_type', )}),
        (u'Cntenido', {'fields': (('title', 'embed_content'), )})
    )


class LiveEmbedEventAdmin(ModelAdmin):
    list_display = (
        'title', 'active', 'access_type', 'in_home', 'notification')
    list_editable = ('access_type', )
    list_filter = ('active', 'access_type')
    fieldsets = (
        (u'Estado', {'fields': ('active', )}),
        (u'Configuración', {'fields': (
            'access_type', 'in_home', 'notification', 'notification_text',
            'notification_url')}),
        (u'Contenido', {'fields': ('title', 'embed_content', 'embed_chat')})
    )


class LugarBaseAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("nombre",)}


class PeliculaEnCineInline(TabularInline):
    model = PeliculaEnCine


class ObraEnTeatroInline(TabularInline):
    model = ObraEnTeatro


class CineAdmin(LugarBaseAdmin):
    model = Cine
    inlines = [PeliculaEnCineInline]


class TeatroAdmin(LugarBaseAdmin):
    model = Teatro
    inlines = [ObraEnTeatroInline]


class PeliculaAdmin(EventoBaseAdmin):
    model = Pelicula
    inlines = [PeliculaEnCineInline]


class ObraAdmin(EventoBaseAdmin):
    model = ObraTeatro
    inlines = [ObraEnTeatroInline]


class CategoriaEventoAdmin(ModelAdmin):
    model = CategoriaEvento


class EventoAdmin(EventoBaseAdmin):
    model = CategoriaEvento
    exclude = ('type',)


site.register(ArchivedEvent, ArchivedEventAdmin)
site.register(LiveEmbedEvent, LiveEmbedEventAdmin)
site.register(Cine, CineAdmin)
site.register(Pelicula, PeliculaAdmin)
site.register(Teatro, TeatroAdmin)
site.register(ObraTeatro, ObraAdmin)
site.register(CategoriaEvento, CategoriaEventoAdmin)
site.register(Evento, EventoAdmin)
