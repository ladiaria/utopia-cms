# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from events.models import Event, Location, Attendant, Activity
from django.contrib.admin import ModelAdmin, site


class LocationAdmin(ModelAdmin):
    pass


class EventAdmin(ModelAdmin):
    fields = ('location', 'title', 'description', 'published', 'date', 'image')
    list_display = ('location', 'title', 'published', 'date')
    list_display_links = ('title',)
    list_filter = ('published', 'date', 'date_created')
    search_fields = ['title']


class AttendantAdmin(ModelAdmin):
    list_display = ('activity', 'name', 'email', 'is_subscriber', 'subscriber')
    list_filter = ('activity', )


class ActivityAdmin(ModelAdmin):
    list_display = ('title', 'date', 'location', 'published', 'closed')


# admin registers
site.register(Location, LocationAdmin)
site.register(Event, EventAdmin)
site.register(Attendant, AttendantAdmin)
site.register(Activity, ActivityAdmin)
