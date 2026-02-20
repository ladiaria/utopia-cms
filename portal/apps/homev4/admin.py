import json

from django.contrib import admin

from .models import HomeLayout
from .views import get_default_grid_data

# Fixed component definitions — order and keys are stable across deployments.
# "description" is a short hint shown in the editor.
COMPONENT_DEFINITIONS = [
    {"key": "apuntes_del_dia",      "label": "Apuntes del día",          "description": ""},
    {"key": "opinion",              "label": "Opinión",                  "description": "Área"},
    {"key": "lo_ultimo",            "label": "Lo último",                "description": "3PM a 6AM"},
    {"key": "recomendadas_lv",      "label": "Recomendadas",             "description": "Lunes a viernes"},
    {"key": "recomendadas_domingo", "label": "Recomendadas Domingo",     "description": "Los domingos"},
    {"key": "lo_mas_leido",         "label": "Lo más leído hoy",         "description": ""},
]


@admin.register(HomeLayout)
class HomeLayoutAdmin(admin.ModelAdmin):
    change_form_template = "homev4/admin_change_form.html"
    list_display = ("name", "publication", "scheduled_time", "is_manual_override", "modified")
    list_filter = ("publication", "is_manual_override")
    list_editable = ("is_manual_override",)
    readonly_fields = ("created", "modified", "manual_override_by", "grid_data")
    fieldsets = (
        (None, {"fields": ("name", "publication", "scheduled_time")}),
        ("Override", {"fields": ("is_manual_override", "manual_override_by")}),
        ("Datos del layout (JSON)", {"fields": ("grid_data",), "classes": ("collapse",)}),
        ("Fechas", {"fields": ("created", "modified")}),
    )
    actions = ["activate_override", "deactivate_override"]

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj:
            grid_data = obj.grid_data if obj.grid_data else get_default_grid_data()
            # Migrate old list format to new dict format automatically
            if isinstance(grid_data, list):
                grid_data = get_default_grid_data()
            extra_context["editor_data"] = self._build_editor_data(grid_data)
            extra_context["save_grid_url"] = f"/homev4/save/{obj.pk}/"
            extra_context["reset_grid_url"] = f"/homev4/reset/{obj.pk}/"
            extra_context["sync_sections_url"] = f"/homev4/sync/{obj.pk}/"
        return super().change_view(request, object_id, form_url, extra_context)

    def _build_editor_data(self, grid_data):
        from core.models import Article, Section, Category, get_current_edition

        result = {
            "inicio_articles": [],
            "sections": [],
            "componentes": [],
        }

        # INICIO articles: DB is source of truth (edition.top_articles with home_top=True).
        # The saved JSON defines the order. Merge rules:
        #   - Articles in saved JSON that are no longer in DB → dropped
        #   - Articles in DB not yet in saved JSON (newly added to edition) → appended at end
        edition = get_current_edition()
        db_articles = list(edition.top_articles) if edition else []
        db_by_id = {a.id: a for a in db_articles}

        saved_ids = grid_data.get("inicio", {}).get("article_ids", [])
        if saved_ids:
            # Apply saved ordering, skip articles no longer in edition
            ordered = [db_by_id[aid] for aid in saved_ids if aid in db_by_id]
            # Append any new edition articles not yet in saved order
            saved_set = set(saved_ids)
            for a in db_articles:
                if a.id not in saved_set:
                    ordered.append(a)
            result["inicio_articles"] = ordered
        else:
            result["inicio_articles"] = db_articles

        # Sections: up to 3 articles each, respecting saved order if available
        for sec_data in grid_data.get("sections", []):
            sec_info = {
                "type": sec_data.get("type", "section"),
                "id": sec_data.get("id"),
                "name": sec_data.get("name", ""),
                "preview_articles": [],
            }
            saved_ids = sec_data.get("article_ids", [])

            if sec_info["type"] == "section" and sec_info["id"]:
                try:
                    section = Section.objects.get(pk=sec_info["id"])
                    sec_info["name"] = section.name
                    if saved_ids:
                        by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
                        sec_info["preview_articles"] = [by_id[aid] for aid in saved_ids if aid in by_id]
                    else:
                        sec_info["preview_articles"] = list(section.latest(limit=3))
                except Section.DoesNotExist:
                    pass
            elif sec_info["type"] == "category" and sec_info["id"]:
                try:
                    category = Category.objects.get(pk=sec_info["id"])
                    sec_info["name"] = category.name
                    if saved_ids:
                        by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
                        sec_info["preview_articles"] = [by_id[aid] for aid in saved_ids if aid in by_id]
                    elif hasattr(category, "home"):
                        sec_info["preview_articles"] = list(category.home.articles_ordered()[:3])
                except Category.DoesNotExist:
                    pass
            result["sections"].append(sec_info)

        # Componentes: merge saved active states with fixed definitions (default active=True)
        saved_comps = grid_data.get("componentes", {})
        for defn in COMPONENT_DEFINITIONS:
            saved = saved_comps.get(defn["key"], {})
            result["componentes"].append({
                "key": defn["key"],
                "label": defn["label"],
                "description": defn["description"],
                "active": saved.get("active", True),
            })

        return result

    @admin.action(description="Activar override manual")
    def activate_override(self, request, queryset):
        queryset.update(is_manual_override=True, manual_override_by=request.user)
        self.message_user(request, f"{queryset.count()} layout(s) activado(s) como override manual.")

    @admin.action(description="Desactivar override manual")
    def deactivate_override(self, request, queryset):
        queryset.update(is_manual_override=False, manual_override_by=None)
        self.message_user(request, f"{queryset.count()} layout(s) desactivado(s).")

    def save_model(self, request, obj, form, change):
        if obj.is_manual_override and not obj.manual_override_by:
            obj.manual_override_by = request.user
        if not obj.grid_data:
            obj.grid_data = get_default_grid_data()
        super().save_model(request, obj, form, change)
