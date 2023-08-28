# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence

from __future__ import unicode_literals
import csv

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse

from .models import Advertiser, AdCategory, AdZone, TextAd, BannerAd, AdClick, AdImpression
from .form import UploadFileForm


@admin.register(Advertiser)
class AdvertiserAdmin(admin.ModelAdmin):
    search_fields = ['company_name', 'website']
    list_display = ['company_name', 'website', 'user']
    raw_id_fields = ['user']


@admin.register(AdCategory)
class AdCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ['title']}
    list_display = ['title', 'slug']


@admin.register(AdZone)
class AdZoneAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'description']


class AdBaseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'start_showing', 'stop_showing', 'category', 'zone']
    list_filter = ['start_showing', 'stop_showing', 'category', 'zone']
    search_fields = ['title', 'url']

    class Media:
        js = ('admin/js/jquery.init.js', 'js/adbase_admin.js')


@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    search_fields = ['ad', 'source_ip']
    list_display = ['ad', 'click_date', 'source_ip']
    list_filter = ['click_date', 'ad']
    date_hierarchy = 'click_date'
    actions = ['download_clicks']

    @admin.action(
        description="Download selected Ad Clicks"
    )
    def download_clicks(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="clicks.csv"'
        writer = csv.writer(response)
        writer.writerow(('Title',
                         'Advertised URL',
                         'Source IP',
                         'Timestamp',
                         'Advertiser ID',
                         'Advertiser name',
                         'Zone'))
        queryset = queryset.select_related('ad', 'ad__advertiser')
        for impression in queryset:
            writer.writerow((impression.ad.title,
                             impression.ad.url,
                             impression.source_ip,
                             impression.click_date.isoformat(),
                             impression.ad.advertiser.pk,
                             impression.ad.advertiser.company_name,
                             impression.ad.zone.title))
        return response

    def get_queryset(self, request):
        qs = super(AdClickAdmin, self).get_queryset(request)
        return qs.select_related('ad').only('ad__title',
                                            'click_date',
                                            'source_ip',)


@admin.register(AdImpression)
class AdImpressionAdmin(admin.ModelAdmin):
    search_fields = ['ad', 'source_ip']
    list_display = ['ad', 'impression_date', 'source_ip']
    list_filter = ['impression_date', 'ad']
    date_hierarchy = 'impression_date'
    actions = ['download_impressions']

    def get_queryset(self, request):
        qs = super(AdImpressionAdmin, self).get_queryset(request)
        return qs.select_related('ad').only('ad__title',
                                            'impression_date',
                                            'source_ip')

    @admin.action(
        description="Download selected Ad Impressions"
    )
    def download_impressions(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="impressions.csv"'
        writer = csv.writer(response)
        writer.writerow(('Title',
                         'Advertised URL',
                         'Source IP',
                         'Timestamp',
                         'Advertiser ID',
                         'Advertiser name',
                         'Zone'))
        queryset = queryset.select_related('ad', 'ad__advertiser')
        for impression in queryset:
            writer.writerow((impression.ad.title,
                             impression.ad.url,
                             impression.source_ip,
                             impression.impression_date.isoformat(),
                             impression.ad.advertiser.pk,
                             impression.ad.advertiser.company_name,
                             impression.ad.zone.title))
        return response


@admin.register(TextAd)
class TextAdAdmin(AdBaseAdmin):
    search_fields = ['title', 'url', 'content']


@admin.register(BannerAd)
class BannerAdAdmin(AdBaseAdmin):
    form = UploadFileForm
    list_display = [
        'title', 'content_basename', 'mobile_content_basename',
        'start_showing', 'stop_showing', 'category', 'zone']
    search_fields = ['title', 'url', 'content', 'mobile_content']
