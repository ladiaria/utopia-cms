import hashlib
import json
import os

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.staticfiles import finders
from django.db.models import Case, IntegerField, Value, When
from django.urls import reverse
from django.utils.html import format_html

from django.utils import timezone

from .models import HomeLayout, HomeLayoutAuditLog, _DAY_CODE_TO_WEEKDAYS
from .views import get_default_grid_data, LAYOUT_BLOCKS_CONFIG, build_editor_data, _static_hash, _SUPLEMENTO_SOURCE_BY_WEEKDAY

# Conditional import: when ADMIN_PAGE_LOCK_ENABLED=True in local_settings.py,
# use AdminLockingMixin to show a warning banner if another user already has the
# layout editor open. Falls back to an empty mixin so no code change is needed
# when the library is not installed or the feature is disabled.
if getattr(settings, 'ADMIN_PAGE_LOCK_ENABLED', False):
    try:
        from admin_locking.admin import AdminLockingMixin
        AdminLockingBase = AdminLockingMixin
    except ImportError:
        class AdminLockingBase:
            pass
else:
    class AdminLockingBase:
        pass


def _static_hash_admin(filename):
    """Return an 8-char MD5 hash of a static file's content for cache busting."""
    path = finders.find(filename)
    if path and os.path.exists(path):
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    return '0'


_DAY_ORDER = {
    "lmjv": 0,
    "ma":   1,
    "lv":   2,
    "lu":   3,
    "mi":   4,
    "ju":   5,
    "vi":   6,
    "sa":   7,
    "do":   8,
}


# Fields that only superusers can modify. Staff users see them as read-only.
_SCHEDULE_FIELDS = ("name", "day", "start_time", "end_time", "ends_next_day", "is_manual_override")


@admin.register(HomeLayout)
class HomeLayoutAdmin(AdminLockingBase, admin.ModelAdmin):
    change_form_template = "homev4/admin_change_form.html"
    list_display = ("name", "publication", "day", "start_time", "end_time", "ends_next_day", "is_manual_override", "modified")
    list_filter = ("is_manual_override",)
    list_editable = ("is_manual_override",)
    readonly_fields = ("publication", "created", "modified", "manual_override_by", "grid_data")
    fieldsets = (
        (None, {"fields": ("name", "publication", "day", "start_time", "end_time", "ends_next_day")}),
        ("Override", {"fields": ("is_manual_override", "manual_override_by")}),
        ("Fechas", {"fields": ("created", "modified")}),
    )
    actions = []

    def get_list_editable(self, request):
        if request.user.is_superuser:
            return ("is_manual_override",)
        return ()

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is None:
            # publication must be set when creating a new layout
            readonly = [f for f in readonly if f != "publication"]
        if not request.user.is_superuser:
            readonly += [f for f in _SCHEDULE_FIELDS if f not in readonly]
        return readonly

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj:
            grid_data = obj.grid_data if isinstance(obj.grid_data, dict) else get_default_grid_data()
            extra_context["editor_data"] = build_editor_data(grid_data, publication=obj.publication)
            extra_context["save_grid_url"] = f"/homev4/save/{obj.pk}/"
            # Slug of today's suplemento source (e.g. "deporte" on Monday, "mundo" on Wednesday).
            # Passed to the editor JS so it can visually dim the matching section in áreas when
            # suplemento is active — purely cosmetic, the section's active flag in grid_data is
            # NOT changed (see layout_editor.js applySuplementoSourceDimming).
            _today_source = _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(timezone.localdate().weekday())
            extra_context["today_suplemento_source_slug"] = _today_source[1] if _today_source else ""
            extra_context["reset_grid_url"] = f"/homev4/reset/{obj.pk}/"
            extra_context["sync_sections_url"] = f"/homev4/sync/{obj.pk}/"
            extra_context["preview_session_url"] = "/homev4/save-preview-session/"
            extra_context["grid_data_pretty"] = json.dumps(obj.grid_data, indent=2, ensure_ascii=False)
            extra_context["blocks_config"] = LAYOUT_BLOCKS_CONFIG
            extra_context["article_search_url"] = f"/homev4/article-search/?layout_id={obj.pk}"
            extra_context["lo_ultimo_latest_url"] = f"/homev4/lo-ultimo-latest/{obj.pk}/"
            extra_context["newsletter_search_url"] = f"/homev4/newsletter-search/?day={obj.day or ''}"
            extra_context["layout_editor_js_version"] = _static_hash("homev4/layout_editor.js")
            extra_context["layout_editor_css_version"] = _static_hash("homev4/layout_editor.css")
        return super().change_view(request, object_id, form_url, extra_context)

    def get_queryset(self, request):
        # Cannot call super() here: the parent's get_queryset applies get_ordering()
        # internally, which references "day_order" before the annotation exists.
        # We annotate first, then order.
        qs = self.model._default_manager.get_queryset()
        day_order = Case(
            *[When(day=day, then=Value(order)) for day, order in _DAY_ORDER.items()],
            default=Value(99),
            output_field=IntegerField(),
        )
        return qs.annotate(day_order=day_order).order_by("day_order", "start_time")


    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Compute the currently active layout pk per publication so the template
        # can highlight the active row without extra queries per row.
        active_pks = []
        pub_ids = HomeLayout.objects.values_list("publication_id", flat=True).distinct()
        from core.models import Publication
        for pub in Publication.objects.filter(pk__in=pub_ids):
            active = HomeLayout.get_active_layout(pub)
            if active:
                active_pks.append(active.pk)
        extra_context["active_layout_pks"] = active_pks
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        if obj.is_manual_override and not obj.manual_override_by:
            obj.manual_override_by = request.user
        if not obj.grid_data:
            obj.grid_data = get_default_grid_data()
        super().save_model(request, obj, form, change)
        self._warn_if_overlap(request, obj)

    class Media:
        js = ('admin_locking/admin_locking.js', 'js/admin_locking_custom.js')

    def _warn_if_overlap(self, request, obj):
        """Show a non-blocking warning if the saved layout overlaps with another scheduled one."""
        if obj.is_manual_override or not (obj.publication_id and obj.day and obj.start_time and obj.end_time):
            return

        def to_minutes(t, next_day=False):
            return t.hour * 60 + t.minute + (1440 if next_day else 0)

        my_weekdays = _DAY_CODE_TO_WEEKDAYS.get(obj.day, set())
        my_start = to_minutes(obj.start_time)
        my_end = to_minutes(obj.end_time, obj.ends_next_day)

        others = HomeLayout.objects.filter(
            publication_id=obj.publication_id, is_manual_override=False,
        ).exclude(pk=obj.pk)

        for other in others:
            if not (other.day and other.start_time and other.end_time):
                continue
            # Two day codes overlap only if they share at least one real weekday
            if not (my_weekdays & _DAY_CODE_TO_WEEKDAYS.get(other.day, set())):
                continue
            other_start = to_minutes(other.start_time)
            other_end = to_minutes(other.end_time, other.ends_next_day)
            # Standard interval overlap: [a, b) overlaps [c, d) iff a < d and c < b
            if my_start < other_end and other_start < my_end:
                url = reverse("admin:homev4_homelayout_change", args=[other.pk])
                self.message_user(
                    request,
                    format_html(
                        'Atención: esta programación se solapa con <a href="{}">{}</a> '
                        "({} {}–{}). En ese horario ganará la que tenga el inicio más tardío.",
                        url,
                        other.name,
                        other.get_day_display(),
                        other.start_time.strftime("%H:%M"),
                        other.end_time.strftime("%H:%M"),
                    ),
                    messages.WARNING,
                )
                return


@admin.register(HomeLayoutAuditLog)
class HomeLayoutAuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "short_save_id", "layout", "user", "triggered_by", "block_key", "ids_before", "ids_after")
    list_filter = ("triggered_by", "block_key", ("layout", admin.RelatedOnlyFieldListFilter))
    search_fields = ("block_key", "user__username", "save_id")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    def short_save_id(self, obj):
        return str(obj.save_id)[:8]
    short_save_id.short_description = "save ID"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name="Layout Editors").exists()
