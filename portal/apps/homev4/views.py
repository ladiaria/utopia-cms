import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Publication, Section, Category

from .models import HomeLayout


DEFAULT_COMPONENTES = {
    "apuntes_del_dia":      {"active": True},
    "opinion":              {"active": True},
    "lo_ultimo":            {"active": True},
    "recomendadas_lv":      {"active": True},
    "recomendadas_domingo": {"active": True},
    "lo_mas_leido":         {"active": True},
}


def get_default_grid_data():
    """
    Build the default layout data.
    Format: {inicio: {article_ids: []}, sections: [{type, id, name}, ...], componentes: {key: {active: bool}}}
    """
    sections = Section.objects.filter(in_home=True).order_by("home_order")
    return {
        "inicio": {"article_ids": []},
        "sections": [
            {"type": "section", "id": s.pk, "name": s.name}
            for s in sections
        ],
        "componentes": dict(DEFAULT_COMPONENTES),
    }


def get_default_publication():
    return Publication.objects.get(slug=settings.DEFAULT_PUB)


@staff_member_required
def save_grid(request, layout_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    layout = get_object_or_404(HomeLayout, pk=layout_id)
    try:
        data = json.loads(request.body)
        grid_data = data.get("grid_data", {})
        layout.grid_data = grid_data
        layout.save()
        # Re-fetch from DB to confirm the save actually persisted
        layout.refresh_from_db(fields=["grid_data"])
        saved_inicio = len(layout.grid_data.get("inicio", {}).get("article_ids", []))
        saved_sections = len(layout.grid_data.get("sections", []))
        return JsonResponse({
            "status": "ok",
            "saved_inicio": saved_inicio,
            "saved_sections": saved_sections,
        })
    except Exception as e:
        import traceback
        return JsonResponse({"error": str(e), "detail": traceback.format_exc()}, status=400)


@staff_member_required
def reset_grid(request, layout_id):
    layout = get_object_or_404(HomeLayout, pk=layout_id)
    layout.grid_data = get_default_grid_data()
    layout.save(update_fields=["grid_data", "modified"])
    return redirect(f"/admin/homev4/homelayout/{layout_id}/change/")


@staff_member_required
def sync_sections(request, layout_id):
    """
    Full sync from DB: rebuilds the sections list (in_home=True, ordered by home_order)
    and clears all saved article_ids so every slot falls back to fresh DB data:
    - INICIO: current edition top_articles
    - Each section: section.latest(limit=3)
    Componentes config is preserved.
    """
    layout = get_object_or_404(HomeLayout, pk=layout_id)
    current = layout.grid_data if isinstance(layout.grid_data, dict) else {}

    componentes = current.get("componentes", {})

    new_sections = [
        {"type": "section", "id": section.pk, "name": section.name}
        for section in Section.objects.filter(in_home=True).order_by("home_order")
    ]

    layout.grid_data = {
        "inicio": {"article_ids": []},
        "sections": new_sections,
        "componentes": componentes,
    }
    layout.save(update_fields=["grid_data", "modified"])
    return redirect(f"/admin/homev4/homelayout/{layout_id}/change/")


@staff_member_required
def sections_json(request):
    sections = list(
        Section.objects.filter(in_home=True).order_by("home_order").values("id", "name", "slug")
    )
    return JsonResponse(sections, safe=False)


@staff_member_required
def categories_json(request):
    categories = list(
        Category.objects.filter(has_newsletter=True).order_by("order").values("id", "name", "slug")
    )
    return JsonResponse(categories, safe=False)