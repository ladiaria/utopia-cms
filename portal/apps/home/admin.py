# -*- coding: utf-8 -*-
from datetime import date, timedelta

from django.contrib.admin import ModelAdmin, StackedInline, site

from core.models import Article
from home.models import Home, HomeArticle, Module


def get_lead_length(obj):
    if obj.lead:
        return len(obj.lead)
    return 0


get_lead_length.short_description = 'Largo del copete'


def was_cover_on(obj):
    covers = ''
    for home in obj.was_cover_on.all():
        covers += '%s, ' % str(home.date)
    if covers != '':
        return covers[:-2]
    return 'Nunca'


was_cover_on.short_description = 'Fue portada'


class HomeArticleAdmin(ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('article', 'lead', 'display')
        }),
    )
    list_display = ('article', get_lead_length, was_cover_on, 'display')
    list_filter = ('article', 'display')
    ordering = ('-article__date_published', 'article__headline')
    search_fields = ['article', 'lead']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        since = date.today() - timedelta(days=1)
        if db_field.name == 'article':
            kwargs['queryset'] = Article.objects.filter(
                date_published__gte=since)
            return db_field.formfield(**kwargs)
        return super(HomeArticleAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)


class ModuleAdminInline(StackedInline):
    model = Module
    raw_id_fields = ['article_%d' % i for i in range(1, 10)]
    readonly_fields = ['article_%d_last_published' % i for i in range(1, 10)]
    fieldsets = tuple([
        (None, {'fields': (
            ('article_%d_last_published' % i, 'article_%d_fixed' % i,
                'article_%d' % i), )}) for i in range(1, 10)])


class HomeAdmin(ModelAdmin):
    inlines = [ModuleAdminInline]
    raw_id_fields = ['cover']
    readonly_fields = ['last_published']
    fieldsets = (
        (None, {'fields': (
            ('category', ), ('last_published', 'fixed', 'cover'), )}), )


site.register(Home, HomeAdmin)
site.register(HomeArticle, HomeArticleAdmin)
