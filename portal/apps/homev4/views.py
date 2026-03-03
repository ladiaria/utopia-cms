import json
import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from core.models import Article, Publication, Section, Category, get_current_edition

from .models import HomeLayout

logger = logging.getLogger("homev4")


DEFAULT_COMPONENTES = [
    {"key": "apuntes_del_dia",      "active": True},
    {"key": "opinion",              "active": True},
    {"key": "lo_ultimo",            "active": True},
    {"key": "recomendadas_lv",      "active": True},
    {"key": "recomendadas_domingo", "active": True},
    {"key": "lo_mas_leido",         "active": True},
]


def get_default_grid_data():
    """
    Build the default layout data.
    Format: {principal: {article_ids: []}, suplemento: {article_ids: []},
             sections: [{type, id, name}, ...], componentes: [{key, active}, ...]}
    """
    sections = Section.objects.filter(in_home=True).order_by("home_order")
    return {
        "principal":  {"active": True, "article_ids": []},
        "suplemento": {"active": True, "article_ids": []},
        "especial":   {"active": True, "article_ids": []},
        "sections": [
            {"type": "section", "id": s.pk, "slug": s.slug, "name": s.name, "row": 1, "active": True}
            for s in sections
        ],
        "componentes": list(DEFAULT_COMPONENTES),
    }


def get_default_publication():
    return Publication.objects.get(slug=settings.DEFAULT_PUB)


def _grid_stats(grid_data):
    """Return a summary dict used both for the save response and for logging."""
    sections = grid_data.get("sections", [])
    componentes = grid_data.get("componentes", [])
    active_comps = [c["key"] for c in componentes if c.get("active", True)]
    return {
        "principal": len(grid_data.get("principal", {}).get("article_ids", [])),
        "suplemento": len(grid_data.get("suplemento", {}).get("article_ids", [])),
        "sections_active": sum(1 for s in sections if s.get("active", True)),
        "sections_total": len(sections),
        "componentes_active": active_comps,
        "componentes_total": len(componentes),
    }


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
        stats = _grid_stats(layout.grid_data)
        logger.debug(
            "save_grid layout=%d user=%s | principal=%d suplemento=%d "
            "sections=%d/%d componentes_active=%s",
            layout.pk,
            request.user,
            stats["principal"],
            stats["suplemento"],
            stats["sections_active"],
            stats["sections_total"],
            stats["componentes_active"],
        )
        return JsonResponse({"status": "ok", **stats})
    except Exception as e:
        import traceback
        logger.exception("save_grid layout=%d error: %s", layout_id, e)
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
        {"type": "section", "id": section.pk, "slug": section.slug, "name": section.name, "row": 1, "active": True}
        for section in Section.objects.filter(in_home=True).order_by("home_order")
    ]

    layout.grid_data = {
        "principal":  {"active": current.get("principal", {}).get("active", True), "article_ids": []},
        "suplemento": {"active": current.get("suplemento", {}).get("active", True), "article_ids": []},
        "especial":   {"active": current.get("especial", {}).get("active", True), "article_ids": []},
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


@never_cache
@staff_member_required
def preview_layout(request, layout_id):
    """Render the home template for a specific layout (opens in new tab from admin)."""
    layout = get_object_or_404(HomeLayout, pk=layout_id)
    grid_data = layout.grid_data if isinstance(layout.grid_data, dict) else {}
    active_comps = [c for c in grid_data.get("componentes", []) if c.get("active")]
    return render(request, "homev4/home.html", {
        "layout": layout,
        "publication": layout.publication,
        "home_data": build_home_data(grid_data),
        "componentes": active_comps,
    })


def build_home_data(grid_data):
    """
    Pre-fetch article objects for every active section in grid_data so the template
    does not need to hit the database.  Returns a dict with:
      principal_active, principal_articles,
      suplemento_active, suplemento_articles,
      especial_active, especial_articles,
      sections (list of dicts, only active ones)
    """
    result = {
        "principal_active": False,
        "principal_articles": [],
        "suplemento_active": False,
        "suplemento_articles": [],
        "especial_active": False,
        "especial_articles": [],
        "sections": [],
    }

    edition = get_current_edition()

    # PRINCIPAL
    principal_data = grid_data.get("principal") or grid_data.get("inicio") or {}
    result["principal_active"] = principal_data.get("active", True)
    if result["principal_active"]:
        db_articles = list(edition.top_articles) if edition else []
        db_by_id = {a.id: a for a in db_articles}
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

    # SUPLEMENTO
    suplemento_data = grid_data.get("suplemento", {})
    result["suplemento_active"] = suplemento_data.get("active", True)
    if result["suplemento_active"]:
        suplemento_ids = suplemento_data.get("article_ids", [])
        if suplemento_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=suplemento_ids)}
            result["suplemento_articles"] = [by_id[aid] for aid in suplemento_ids if aid in by_id]

    # ESPECIAL
    especial_data = grid_data.get("especial", {})
    result["especial_active"] = especial_data.get("active", True)
    if result["especial_active"]:
        especial_ids = especial_data.get("article_ids", [])
        if especial_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=especial_ids)}
            result["especial_articles"] = [by_id[aid] for aid in especial_ids if aid in by_id]

    # SECTIONS — only active ones
    for sec_data in grid_data.get("sections", []):
        if not sec_data.get("active", True):
            continue
        sec_type = sec_data.get("type", "section")
        sec_id = sec_data.get("id")
        sec_slug = sec_data.get("slug")
        sec_name = sec_data.get("name", "")
        sec_row = sec_data.get("row", 1)
        saved_ids = sec_data.get("article_ids", [])
        articles = []
        url = ""

        if sec_type == "section" and (sec_slug or sec_id):
            try:
                section = Section.objects.get(slug=sec_slug) if sec_slug else Section.objects.get(pk=sec_id)
                sec_name = section.name
                url = section.get_absolute_url()
                if saved_ids:
                    by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
                    articles = [by_id[aid] for aid in saved_ids if aid in by_id]
                else:
                    articles = list(section.latest(limit=3))
            except Section.DoesNotExist:
                pass
        elif sec_type == "category" and sec_id:
            try:
                category = Category.objects.get(pk=sec_id)
                sec_name = category.name
                url = f"/{category.slug}/"
                if saved_ids:
                    by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
                    articles = [by_id[aid] for aid in saved_ids if aid in by_id]
                elif hasattr(category, "home"):
                    articles = list(category.home.articles_ordered()[:3])
            except Category.DoesNotExist:
                pass

        result["sections"].append({
            "type": sec_type,
            "id": sec_id,
            "slug": sec_slug,
            "name": sec_name,
            "row": sec_row,
            "url": url,
            "articles": articles,
        })

    return result


def active_layout(request, publication_slug=None):
    if publication_slug:
        publication = get_object_or_404(Publication, slug=publication_slug)
    else:
        publication = get_default_publication()
    layout = HomeLayout.get_active_layout(publication)
    if layout is None:
        return render(request, "homev4/home.html", {
            "layout": None,
            "publication": publication,
            "home_data": {},
            "componentes": [],
        })
    grid_data = layout.grid_data if isinstance(layout.grid_data, dict) else {}
    active_comps = [c for c in grid_data.get("componentes", []) if c.get("active")]
    home_data = build_home_data(grid_data)
    return render(request, "homev4/home.html", {
        "layout": layout,
        "publication": publication,
        "home_data": home_data,
        "principal_active": home_data["principal_active"],
        "suplemento_active": home_data["suplemento_active"],
        "especial_active": home_data["especial_active"],
        "componentes": active_comps,
    })