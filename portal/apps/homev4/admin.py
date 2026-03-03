import json

from django.contrib import admin
from django.db.models import Case, IntegerField, Value, When

from .models import HomeLayout
from .views import get_default_grid_data

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

# Fixed component definitions — keys must stay stable; label/description can change.
COMPONENT_DEFINITIONS = [
    {"key": "apuntes_del_dia",      "label": "Apuntes del día",          "description": ""},
    {"key": "opinion",              "label": "Opinión",                  "description": "Área"},
    {"key": "lo_ultimo",            "label": "Lo último",                "description": "3PM a 6AM"},
    {"key": "radio",                "label": "Radio",                    "description": ""},
    {"key": "recomendadas_lv",      "label": "Recomendadas",             "description": "Lunes a viernes"},
    {"key": "newsletter_dia",       "label": "Newsletter del día",       "description": ""},
    {"key": "recomendadas_domingo", "label": "Recomendadas Domingo",     "description": "Los domingos"},
    {"key": "lo_mas_leido",         "label": "Lo más leído hoy",         "description": ""},
]

# Placeholder articles shown in the editor until real data sources are defined.
COMPONENT_PLACEHOLDER_ARTICLES = {
    "apuntes_del_dia": [
        "Primer artículo de Apuntes del día",
        "Segundo artículo de Apuntes del día",
        "Tercer artículo de Apuntes del día",
    ],
    "opinion": [
        "Primera columna de opinión",
        "Segunda columna de opinión",
        "Tercera columna de opinión",
    ],
    "lo_ultimo": [
        "Último artículo publicado 1",
        "Último artículo publicado 2",
        "Último artículo publicado 3",
    ],
    "recomendadas_lv": [
        "Recomendado lunes a viernes 1",
        "Recomendado lunes a viernes 2",
        "Recomendado lunes a viernes 3",
    ],
    "recomendadas_domingo": [
        "Recomendado domingo 1",
        "Recomendado domingo 2",
        "Recomendado domingo 3",
    ],
    "lo_mas_leido": [
        "Artículo más leído hoy 1",
        "Artículo más leído hoy 2",
        "Artículo más leído hoy 3",
    ],
}

_COMP_DEF_MAP = {d["key"]: d for d in COMPONENT_DEFINITIONS}


@admin.register(HomeLayout)
class HomeLayoutAdmin(admin.ModelAdmin):
    change_form_template = "homev4/admin_change_form.html"
    list_display = ("name", "publication", "day", "start_time", "end_time", "ends_next_day", "is_manual_override", "modified")
    list_filter = ("publication", "is_manual_override")
    list_editable = ("is_manual_override",)
    readonly_fields = ("created", "modified", "manual_override_by", "grid_data")
    fieldsets = (
        (None, {"fields": ("name", "publication", "day", "start_time", "end_time", "ends_next_day")}),
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
            extra_context["preview_url"] = f"/homev4/preview/{obj.pk}/"
        return super().change_view(request, object_id, form_url, extra_context)

    def _build_editor_data(self, grid_data):
        from core.models import Article, Section, Category, get_current_edition

        principal_data = grid_data.get("principal") or grid_data.get("inicio") or {}
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

        edition = get_current_edition()

        # PRINCIPAL articles: DB is source of truth (edition.top_articles with home_top=True).
        # Saved JSON defines the order. Merge rules:
        #   - Articles in saved JSON no longer in DB → dropped
        #   - New DB articles not in saved JSON → appended at end
        db_articles = list(edition.top_articles) if edition else []
        db_by_id = {a.id: a for a in db_articles}

        # Support migration from old "inicio" key to "principal"
        principal_data = grid_data.get("principal") or grid_data.get("inicio") or {}
        saved_ids = principal_data.get("article_ids", [])
        if saved_ids:
            ordered = [db_by_id[aid] for aid in saved_ids if aid in db_by_id]
            saved_set = set(saved_ids)
            for a in db_articles:
                if a.id not in saved_set:
                    ordered.append(a)
            result["principal_articles"] = ordered
        else:
            result["principal_articles"] = db_articles

        # SUPLEMENTO articles: same merge logic, independent list
        # TODO: define DB source when the user clarifies which section/edition feeds SUPLEMENTO
        suplemento_saved_ids = grid_data.get("suplemento", {}).get("article_ids", [])
        if suplemento_saved_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=suplemento_saved_ids)}
            result["suplemento_articles"] = [by_id[aid] for aid in suplemento_saved_ids if aid in by_id]
        else:
            result["suplemento_articles"] = []

        # Sections: up to 3 articles each, respecting saved order if available
        for sec_data in grid_data.get("sections", []):
            sec_info = {
                "type": sec_data.get("type", "section"),
                "id": sec_data.get("id"),
                "slug": sec_data.get("slug"),
                "name": sec_data.get("name", ""),
                "row": sec_data.get("row", 1),
                "active": sec_data.get("active", True),
                "preview_articles": [],
            }
            saved_ids = sec_data.get("article_ids", [])

            if sec_info["type"] == "section" and (sec_info["slug"] or sec_info["id"]):
                try:
                    section = (
                        Section.objects.get(slug=sec_info["slug"])
                        if sec_info["slug"]
                        else Section.objects.get(pk=sec_info["id"])
                    )
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

        # Componentes: merge saved order/active states with fixed definitions.
        # Saved format can be:
        #   - list (new): [{key, active}, ...]  — preserves custom drag order
        #   - dict (old): {key: {active: bool}} — migrated to list order on next save
        saved_comps_raw = grid_data.get("componentes", [])
        def _apply_article_order(placeholders, order):
            """Reorder placeholder list according to saved index order."""
            if order and len(order) == len(placeholders):
                try:
                    return [placeholders[i] for i in order]
                except IndexError:
                    pass
            return placeholders

        if isinstance(saved_comps_raw, list):
            seen_keys = set()
            for item in saved_comps_raw:
                key = item.get("key", "")
                defn = _COMP_DEF_MAP.get(key)
                if defn and key not in seen_keys:
                    seen_keys.add(key)
                    placeholders = COMPONENT_PLACEHOLDER_ARTICLES.get(key, [])
                    result["componentes"].append({
                        "key": key,
                        "label": defn["label"],
                        "description": defn["description"],
                        "active": item.get("active", True),
                        "articles": _apply_article_order(placeholders, item.get("article_order")),
                    })
            # Append any definitions not present in the saved list
            for defn in COMPONENT_DEFINITIONS:
                if defn["key"] not in seen_keys:
                    result["componentes"].append({
                        "key": defn["key"],
                        "label": defn["label"],
                        "description": defn["description"],
                        "active": True,
                        "articles": COMPONENT_PLACEHOLDER_ARTICLES.get(defn["key"], []),
                    })
        else:
            # Old dict format — use fixed definition order
            for defn in COMPONENT_DEFINITIONS:
                saved = saved_comps_raw.get(defn["key"], {})
                result["componentes"].append({
                    "key": defn["key"],
                    "label": defn["label"],
                    "description": defn["description"],
                    "active": saved.get("active", True),
                    "articles": COMPONENT_PLACEHOLDER_ARTICLES.get(defn["key"], []),
                })

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
