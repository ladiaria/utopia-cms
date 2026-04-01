import hashlib
import json
import os

from django.contrib import admin, messages
from django.contrib.staticfiles import finders
from django.db.models import Case, IntegerField, Value, When
from django.urls import reverse
from django.utils.html import format_html

from .models import HomeLayout, _DAY_CODE_TO_WEEKDAYS
from .views import get_default_grid_data, COMPONENT_DEFINITIONS, _COMP_DEF_MAP, _fetch_component_articles, _fetch_suplemento_articles, LAYOUT_BLOCKS_CONFIG, _resolve_newsletter_refs

def _static_hash(filename):
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
class HomeLayoutAdmin(admin.ModelAdmin):
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
            extra_context["editor_data"] = self._build_editor_data(grid_data, publication=obj.publication)
            extra_context["save_grid_url"] = f"/homev4/save/{obj.pk}/"
            extra_context["reset_grid_url"] = f"/homev4/reset/{obj.pk}/"
            extra_context["sync_sections_url"] = f"/homev4/sync/{obj.pk}/"
            extra_context["preview_url"] = f"/homev4/preview/{obj.pk}/"
            extra_context["grid_data_pretty"] = json.dumps(obj.grid_data, indent=2, ensure_ascii=False)
            extra_context["blocks_config"] = LAYOUT_BLOCKS_CONFIG
            extra_context["article_search_url"] = f"/homev4/article-search/?layout_id={obj.pk}"
            extra_context["newsletter_search_url"] = f"/homev4/newsletter-search/?day={obj.day or ''}"
            extra_context["layout_editor_js_version"] = _static_hash('homev4/layout_editor.js')
            extra_context["layout_editor_css_version"] = _static_hash('homev4/layout_editor.css')
        return super().change_view(request, object_id, form_url, extra_context)

    def _build_editor_data(self, grid_data, publication=None):
        from core.models import Article, Section, Category, get_current_edition

        principal_data = grid_data.get("principal") or {}
        suplemento_data = grid_data.get("suplemento", {})
        especial_data = grid_data.get("especial", {})

        result = {
            "principal_active": principal_data.get("active", True),
            "principal_articles": [],
            "suplemento_active": suplemento_data.get("active", True),
            "suplemento_articles": [],
            "especial_active": especial_data.get("active", True),
            "especial_articles": [],
            "sections": [],
            "componentes": [],
        }

        edition = get_current_edition(publication=publication)

        # PRINCIPAL: if saved_ids present, show exactly those (in order); else fall back to edition.top_articles.
        db_articles = list(edition.top_articles) if edition else []

        principal_data = grid_data.get("principal") or {}
        saved_ids = principal_data.get("article_ids", [])
        if saved_ids:
            by_id = {a.id: a for a in db_articles}
            extra_ids = [aid for aid in saved_ids if aid not in by_id]
            if extra_ids:
                by_id.update({a.id: a for a in Article.published.filter(id__in=extra_ids)})
            result["principal_articles"] = [by_id[aid] for aid in saved_ids if aid in by_id]
        else:
            result["principal_articles"] = db_articles

        # SUPLEMENTO articles: saved_ids if saved today, else day-based section fallback.
        try:
            result["suplemento_articles"] = _fetch_suplemento_articles(
                grid_data.get("suplemento", {}).get("article_ids", []),
                grid_data.get("suplemento", {}).get("saved_date"),
            )
        except Exception:
            result["suplemento_articles"] = []

        # ESPECIAL articles: resolve saved_ids to Article objects.
        especial_ids = especial_data.get("article_ids", [])
        if especial_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=especial_ids)}
            result["especial_articles"] = [by_id[aid] for aid in especial_ids if aid in by_id]

        # ÁREAS Y PUBLICACIONES: source of truth is grid_data["sections"] merged with _DEFAULT_AREAS.
        # Areas in _DEFAULT_AREAS not yet in grid_data are appended automatically (same as components).
        from .views import _fetch_area_articles, _DEFAULT_AREAS
        saved_areas = grid_data.get("sections", [])
        saved_area_keys = {(s.get("type"), s.get("slug")) for s in saved_areas}
        merged_areas = list(saved_areas) + [
            {"type": a["type"], "slug": a["slug"], "name": a["name"], "active": True, "article_ids": []}
            for a in _DEFAULT_AREAS if (a["type"], a["slug"]) not in saved_area_keys
        ]
        for area in merged_areas:
            area_type = area.get("type", "section")
            slug = area.get("slug", "")
            if not slug:
                continue
            saved_ids = area.get("article_ids", [])
            sec_info = {
                "type": area_type,
                "slug": slug,
                "name": area.get("name", slug),
                "active": area.get("active", True),
                "preview_articles": [],
            }
            if saved_ids:
                by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
                sec_info["preview_articles"] = [by_id[aid] for aid in saved_ids if aid in by_id]
            else:
                sec_info["preview_articles"] = _fetch_area_articles(area_type, slug, [])
            result["sections"].append(sec_info)

        # Componentes: merge saved order/active states with fixed definitions.
        # Saved format can be:
        #   - list (new): [{key, active}, ...]  — preserves custom drag order
        #   - dict (old): {key: {active: bool}} — migrated to list order on next save
        saved_comps_raw = grid_data.get("componentes", [])

        if isinstance(saved_comps_raw, list):
            seen_keys = set()
            for item in saved_comps_raw:
                key = item.get("key", "")
                defn = _COMP_DEF_MAP.get(key)
                if defn and key not in seen_keys:
                    seen_keys.add(key)
                    comp_dict = {
                        "key": key,
                        "label": defn["label"],
                        "description": defn["description"],
                        "active": item.get("active", True),
                        "has_picker": defn.get("has_picker", False),
                        "replace_mode": defn.get("replace_mode", False),
                        "replace_slots": defn.get("replace_slots", 2),
                        "newsletter_mode": defn.get("newsletter_mode", False),
                        "sortable_articles": defn.get("sortable_articles", True),
                    }
                    if defn.get("newsletter_mode"):
                        comp_dict["newsletters"] = _resolve_newsletter_refs(item.get("newsletter_refs", []))
                        comp_dict["articles"] = []
                    else:
                        comp_dict["articles"] = _fetch_component_articles(key, saved_ids=item.get("article_ids", []))
                    result["componentes"].append(comp_dict)
            # Append any definitions not present in the saved list
            for defn in COMPONENT_DEFINITIONS:
                if defn["key"] not in seen_keys:
                    comp_dict = {
                        "key": defn["key"],
                        "label": defn["label"],
                        "description": defn["description"],
                        "active": True,
                        "has_picker": defn.get("has_picker", False),
                        "replace_mode": defn.get("replace_mode", False),
                        "replace_slots": defn.get("replace_slots", 2),
                        "newsletter_mode": defn.get("newsletter_mode", False),
                        "sortable_articles": defn.get("sortable_articles", True),
                    }
                    if defn.get("newsletter_mode"):
                        comp_dict["newsletters"] = []
                        comp_dict["articles"] = []
                    else:
                        comp_dict["articles"] = _fetch_component_articles(defn["key"])
                    result["componentes"].append(comp_dict)
        else:
            # Old dict format — use fixed definition order
            for defn in COMPONENT_DEFINITIONS:
                saved = saved_comps_raw.get(defn["key"], {})
                comp_dict = {
                    "key": defn["key"],
                    "label": defn["label"],
                    "description": defn["description"],
                    "active": saved.get("active", True),
                    "has_picker": defn.get("has_picker", False),
                    "replace_mode": defn.get("replace_mode", False),
                    "replace_slots": defn.get("replace_slots", 2),
                    "newsletter_mode": defn.get("newsletter_mode", False),
                    "sortable_articles": defn.get("sortable_articles", True),
                }
                if defn.get("newsletter_mode"):
                    comp_dict["newsletters"] = _resolve_newsletter_refs(saved.get("newsletter_refs", []))
                    comp_dict["articles"] = []
                else:
                    comp_dict["articles"] = _fetch_component_articles(defn["key"])
                result["componentes"].append(comp_dict)

        return result

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
