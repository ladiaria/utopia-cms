from django.contrib.admin import ModelAdmin


class ReadOnlyModelAdmin(ModelAdmin):
    """ A read-only modeladmin, no action can be performed, only see the object list """
    list_display_links = None
    actions = None

    def changelist_view(self, request, extra_context=None):
        extra_context = {'title': self.model._meta.verbose_name_plural.capitalize()}
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    has_delete_permission = has_change_permission
