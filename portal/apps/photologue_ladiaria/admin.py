# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin

from photologue.models import Photo, Gallery, PhotoEffect, PhotoSize, Watermark
from photologue.admin import PhotoAdmin as PhotoAdminDefault
from photologue.admin import GalleryAdmin as GalleryAdminDefault

from .models import PhotoExtended, Agency, Photographer


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    pass


class PhotoExtendedModelForm(forms.ModelForm):
    date_taken = forms.DateField(label='Tomada el', widget=admin.widgets.AdminDateWidget(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.id:
            self.initial['date_taken'] = self.instance.image.date_taken

    def save(self, commit=True):
        instance = super().save(commit=commit)
        instance.image.date_taken = self.cleaned_data['date_taken']
        if not instance.image._old_image:
            # this is a new image, we need to "fake" the old image to avoid photologue.Photo attemp to rm a "None" file
            instance.image._old_image = instance.image.image
        instance.image.save()
        return instance

    class Meta:
        model = PhotoExtended
        fields = ('date_taken',)


class PhotoExtendedInline(admin.StackedInline):
    model = PhotoExtended
    form = PhotoExtendedModelForm
    can_delete = False
    fieldsets = (
        ('Metadatos', {'fields': ('date_taken', 'type', 'photographer', 'agency')}),
        (
            'Recorte para versión cuadrada',
            {'fields': ('focuspoint_x', 'focuspoint_y', 'radius_length'), 'classes': ('collapse',)}
        ),
    )

    class Media:
        js = ('js/jquery.cropbox.js',)
        css = {"all": ("css/headless_stacked_inline.css",)}


class PhotoGalleryInline(admin.TabularInline):
    model = Gallery.photos.through
    raw_id_fields = ('photo',)
    extra = 0
    verbose_name = 'foto'
    verbose_name_plural = 'fotos'
    readonly_fields = ['photo_admin_thumbnail', 'photo_date_taken', 'photo_date_added']

    @admin.display(
        description='thumbnail'
    )
    def photo_admin_thumbnail(self, instance):
        return instance.photo.admin_thumbnail()

    @admin.display(
        description='tomada el'
    )
    def photo_date_taken(self, instance):
        return instance.photo.date_taken

    @admin.display(
        description='fecha de creación'
    )
    def photo_date_added(self, instance):
        return instance.photo.date_added


class GalleryAdmin(GalleryAdminDefault):
    list_display = ('title', 'date_added', 'photo_count', 'is_public')
    list_filter = ['date_added', 'is_public']
    date_hierarchy = 'date_added'
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('photos',)
    inlines = [PhotoGalleryInline]
    exclude = ('photos',)


@admin.register(Photographer)
class PhotographerAdmin(admin.ModelAdmin):
    search_fields = ('name',)


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


class AgencyFilter(admin.SimpleListFilter):
    title = 'agency'
    parameter_name = 'agency'

    def lookups(self, request, model_admin):
        return [(a.id, a.name) for a in Agency.objects.all() if a.photos.exists()]

    def queryset(self, request, queryset):
        agency = self.value()
        return queryset.filter(
            id__in=PhotoExtended.objects.filter(agency=agency).values_list('image', flat=True)
        ) if agency else queryset


class PhotographerFilter(admin.SimpleListFilter):
    title = 'photographer'
    parameter_name = 'photographer'

    def lookups(self, request, model_admin):
        return [(p.id, p.name) for p in Photographer.objects.all() if p.photos.exists()]

    def queryset(self, request, queryset):
        photographer = self.value()
        return queryset.filter(
            id__in=PhotoExtended.objects.filter(photographer=photographer).values_list('image', flat=True)
        ) if photographer else queryset


class PhotoAdmin(PhotoAdminDefault):
    list_display = ('title', 'admin_thumbnail', 'date_taken', 'date_added', 'is_public', 'view_count')
    list_filter = tuple(PhotoAdminDefault.list_filter) + (AgencyFilter, PhotographerFilter)
    fieldsets = (
        (None, {'fields': ('title', 'image', 'caption')}),
        ('Avanzado', {'fields': ('slug', 'crop_from', 'is_public'), 'classes': ('collapse',)}))
    inlines = [PhotoExtendedInline]


admin.site.unregister(Photo)
admin.site.register(Photo, PhotoAdmin)

admin.site.unregister(Gallery)
admin.site.register(Gallery, GalleryAdmin)


admin.site.unregister(PhotoEffect)
admin.site.register(PhotoEffect, PhotoEffectAdmin)

admin.site.unregister(PhotoSize)
admin.site.register(PhotoSize, PhotoSizeAdmin)

admin.site.unregister(Watermark)
admin.site.register(Watermark, WatermarkAdmin)
