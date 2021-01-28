# -*- coding: utf-8 -*-
from django.conf import settings
from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget

from photologue.models import Photo, Gallery, PhotoEffect, PhotoSize, Watermark
from photologue.admin import PhotoAdmin as PhotoAdminDefault
from photologue.admin import GalleryAdmin as GalleryAdminDefault

from models import PhotoExtended, Agency, Photographer


class AgencyAdmin(admin.ModelAdmin):
    pass


class PhotoExtendedModelForm(forms.ModelForm):
    date_taken = forms.DateField(label=u'Tomada el', widget=AdminDateWidget(), required=False)

    def __init__(self, *args, **kwargs):
        super(PhotoExtendedModelForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            self.initial['date_taken'] = self.instance.image.date_taken

    def save(self, commit=True):
        instance = super(PhotoExtendedModelForm, self).save(commit=commit)
        instance.image.date_taken = self.cleaned_data['date_taken']
        instance.image.save()
        return instance

    class Meta:
        model = PhotoExtended


class PhotoExtendedInline(admin.StackedInline):
    model = PhotoExtended
    form = PhotoExtendedModelForm
    can_delete = False
    fieldsets = (
        ('Metadatos', {'fields': ('date_taken', 'type', 'photographer', 'agency')}),
        (u'Recorte para versión cuadrada', {
            'fields': ('focuspoint_x', 'focuspoint_y', 'radius_length'), 'classes': ('collapse', )}))

    class Media:
        # jquery loaded again (admin uses custom js namespaces)
        js = ('admin/js/jquery%s.js' % ('' if settings.DEBUG else '.min'), 'js/jquery.cropbox.js')


class PhotoGalleryInline(admin.TabularInline):
    model = Gallery.photos.through
    raw_id_fields = ('photo', )
    extra = 0
    verbose_name = u'foto'
    verbose_name_plural = u'fotos'
    readonly_fields = ['photo_admin_thumbnail', 'photo_date_taken', 'photo_date_added']

    def photo_admin_thumbnail(self, instance):
        return instance.photo.admin_thumbnail()
    photo_admin_thumbnail.short_description = u'thumbnail'
    photo_admin_thumbnail.allow_tags = True

    def photo_date_taken(self, instance):
        return instance.photo.date_taken
    photo_date_taken.short_description = u'tomada el'

    def photo_date_added(self, instance):
        return instance.photo.date_added
    photo_date_added.short_description = u'fecha de creación'


class GalleryAdmin(GalleryAdminDefault):
    list_display = ('title', 'date_added', 'photo_count', 'is_public')
    list_filter = ['date_added', 'is_public']
    date_hierarchy = 'date_added'
    prepopulated_fields = {'title_slug': ('title',)}
    filter_horizontal = ('photos',)
    inlines = [PhotoGalleryInline]
    exclude = ('photos', )


class PhotographerAdmin(admin.ModelAdmin):
    search_fields = ('name', )


class PhotoEffectAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'description', 'color', 'brightness', 'contrast', 'sharpness',
        'filters', 'admin_sample')
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Adjustments', {
            'fields': ('color', 'brightness', 'contrast', 'sharpness')
        }),
        ('Filters', {
            'fields': ('filters',)
        }),
        ('Reflection', {
            'fields': (
                'reflection_size', 'reflection_strength', 'background_color')
        }),
        ('Transpose', {
            'fields': ('transpose_method',)
        }),
    )


class PhotoSizeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'width', 'height', 'crop', 'pre_cache', 'effect',
        'increment_count')
    fieldsets = (
        (None, {
            'fields': ('name', 'width', 'height', 'quality')
        }),
        ('Options', {
            'fields': ('upscale', 'crop', 'pre_cache', 'increment_count')
        }),
        ('Enhancements', {
            'fields': ('effect', 'watermark',)
        }),
    )


class WatermarkAdmin(admin.ModelAdmin):
    list_display = ('name', 'opacity', 'style')


# TODO: make filters by agency and photographer (lost features when upgraded to Django1.5)
class PhotoAdmin(PhotoAdminDefault):
    list_display = ('title', 'admin_thumbnail', 'date_taken', 'date_added', 'is_public', 'view_count')
    fieldsets = (
        (None, {'fields': ('title', 'image', 'caption')}),
        ('Avanzado', {'fields': ('title_slug', 'crop_from', 'is_public'), 'classes': ('collapse', )}))
    inlines = [PhotoExtendedInline]


admin.site.unregister(Photo)
admin.site.register(Photo, PhotoAdmin)

admin.site.unregister(Gallery)
admin.site.register(Gallery, GalleryAdmin)

admin.site.register(Agency, AgencyAdmin)
admin.site.register(Photographer, PhotographerAdmin)

admin.site.unregister(PhotoEffect)
admin.site.register(PhotoEffect, PhotoEffectAdmin)

admin.site.unregister(PhotoSize)
admin.site.register(PhotoSize, PhotoSizeAdmin)

admin.site.unregister(Watermark)
admin.site.register(Watermark, WatermarkAdmin)
