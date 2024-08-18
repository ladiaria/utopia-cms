from django.contrib import admin
from .models import EpubFile


class ArticleAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'bajada',)

#admin.site.register(Article, ArticleAdmin)

admin.site.register(EpubFile)
#admin.site.register(Section)
