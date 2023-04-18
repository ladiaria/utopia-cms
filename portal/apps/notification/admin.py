from __future__ import unicode_literals
from django.contrib import admin

from notification.models import NoticeType, NoticeSetting, NoticeQueueBatch


@admin.register(NoticeType)
class NoticeTypeAdmin(admin.ModelAdmin):
    list_display = ["label", "display", "description", "default"]


@admin.register(NoticeSetting)
class NoticeSettingAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "notice_type", "medium", "send"]
    raw_id_fields = ('user', )


admin.site.register(NoticeQueueBatch)
