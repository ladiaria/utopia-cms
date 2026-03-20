import datetime
import json
import logging
import time

from django.utils import timezone

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.vary import vary_on_cookie

from core.models import Article, Publication, Section, Category, get_current_edition
from core.views.masleidos import mas_leidos
from thedaily.utils import unsubscribed_newsletters

from decorators import decorate_if_no_auth, decorate_if_auth

from .models import HomeLayout

logger = logging.getLogger("homev4")

_cache_maxage = getattr(settings, "HOMEV3_INDEX_CACHE_MAXAGE", 120)


def _log_timing(view_func):
    def wrapper(request, *args, **kwargs):
        t0 = time.perf_counter()
        response = view_func(request, *args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.warning("active_layout timing: %.1f ms (user_auth=%s)", elapsed, request.user.is_authenticated)
        return response
    wrapper.__name__ = view_func.__name__
    return wrapper

# select_related chain for article queries that feed _add_auth_context.
# Ensures is_restricted() does not trigger lazy loads (main_section → edition → publication)
# per article. Update this constant if the chain changes in the Article/ArticleRel models.
_ARTICLE_AUTH_SELECT_RELATED = "main_section__edition__publication"


def _block_active(block_key, saved_flag):
    """Return the effective active state for a top-level block.
    If LAYOUT_BLOCKS_CONFIG defines always_active for the block, that wins.
    Otherwise falls back to the saved flag from grid_data.
    """
    config = LAYOUT_BLOCKS_CONFIG.get(block_key, {})
    if config.get("always_active") is True:
        return True
    return saved_flag


# Fixed component definitions — keys must stay stable; label/description can change.
COMPONENT_DEFINITIONS = [
    {"key": "apuntes_del_dia",      "label": "Apuntes del día",          "description": "",                "sortable_articles": False},
    {"key": "opinion",              "label": "Opinión",                  "description": "Área",            "has_picker": True},
    {"key": "lo_ultimo",            "label": "Lo último",                "description": "3PM a 6AM",       "sortable_articles": False},
    {"key": "radio",                "label": "Radio",                    "description": ""},
    {"key": "recomendadas_lv",      "label": "Recomendadas",             "description": "Lunes a viernes", "has_picker": True},
    {"key": "newsletter_dia",       "label": "Newsletter del día",       "description": ""},
    {"key": "recomendadas_domingo", "label": "Recomendadas Domingo",     "description": "Los domingos",    "has_picker": True},
    {"key": "lo_mas_leido",         "label": "Lo más leído hoy",         "description": "",                "sortable_articles": False},
    {"key": "le_monde",             "label": "Le Monde Diplomatique",    "description": "",                "has_picker": True},
    {"key": "lento",                "label": "Lento",                    "description": "",                "has_picker": True},
]

_COMP_DEF_MAP = {d["key"]: d for d in COMPONENT_DEFINITIONS}

DEFAULT_COMPONENTES = [{"key": d["key"], "active": True} for d in COMPONENT_DEFINITIONS]

# Defines which top-level blocks have a fixed active state that cannot be toggled in the editor.
LAYOUT_BLOCKS_CONFIG = {
    "principal":  {"always_active": True},
    "suplemento": {"always_active": False},
    "especial":   {"always_active": False},

}


def get_default_grid_data():
    """
    Build the default layout data.
    Format: {principal: {article_ids: []}, suplemento: {article_ids: []},
             sections: [{type, slug, name, active, article_ids}, ...], componentes: [{key, active}, ...]}
    """
    return {
        "principal":  {"active": True, "article_ids": []},
        "suplemento": {"active": True, "article_ids": []},
        "especial":   {"active": True, "article_ids": []},
        "sections": [
            {"type": a["type"], "slug": a["slug"], "name": a["name"], "active": True, "article_ids": []}
            for a in _DEFAULT_AREAS
        ],
        "componentes": list(DEFAULT_COMPONENTES),
    }


def get_default_publication():
    return Publication.objects.get(slug=settings.DEFAULT_PUB)


def _propagate_article_ids(source_layout, source_grid):
    """
    Copy article_ids from source_grid to all other layouts of the same publication.
    Active/inactive flags in each target layout are preserved.
    Called after save_grid so that all layouts stay in sync.
    """
    others = list(HomeLayout.objects.exclude(pk=source_layout.pk).filter(publication=source_layout.publication))
    if not others:
        return

    src_top = {
        block: source_grid.get(block, {}).get("article_ids", [])
        for block in ("principal", "suplemento", "especial")
    }
    src_sections = {s["slug"]: s.get("article_ids", []) for s in source_grid.get("sections", [])}
    src_componentes = {c["key"]: c.get("article_ids", []) for c in source_grid.get("componentes", [])}

    now = timezone.now()
    for layout in others:
        gd = layout.grid_data if isinstance(layout.grid_data, dict) else {}

        for block, ids in src_top.items():
            block_data = gd.get(block) if isinstance(gd.get(block), dict) else {}
            block_data["article_ids"] = ids
            gd[block] = block_data

        for sec in gd.get("sections", []):
            if sec.get("slug") in src_sections:
                sec["article_ids"] = src_sections[sec["slug"]]

        for comp in gd.get("componentes", []):
            if comp.get("key") in src_componentes:
                comp["article_ids"] = src_componentes[comp["key"]]

        layout.grid_data = gd
        layout.modified = now

    HomeLayout.objects.bulk_update(others, ["grid_data", "modified"])
    logger.debug("_propagate_article_ids: synced layout=%d to %d others", source_layout.pk, len(others))


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
        _propagate_article_ids(layout, layout.grid_data)
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
        {"type": a["type"], "slug": a["slug"], "name": a["name"], "active": True, "article_ids": []}
        for a in _DEFAULT_AREAS
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


@staff_member_required
def article_search(request):
    """Return up to 10 published articles matching the ?q= headline search (for the picker widget).
    Excludes articles already assigned to any zone of the current layout (?layout_id=).
    """
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)

    excluded_ids = set()
    layout_id = request.GET.get("layout_id")
    if layout_id:
        try:
            layout = HomeLayout.objects.get(pk=layout_id)
            gd = layout.grid_data if isinstance(layout.grid_data, dict) else {}
            for block in ("principal", "suplemento", "especial"):
                excluded_ids.update(gd.get(block, {}).get("article_ids", []))
            for sec in gd.get("sections", []):
                excluded_ids.update(sec.get("article_ids", []))
            for comp in gd.get("componentes", []):
                excluded_ids.update(comp.get("article_ids", []))
        except HomeLayout.DoesNotExist:
            pass

    qs = Article.published.filter(headline__icontains=q)
    if excluded_ids:
        qs = qs.exclude(id__in=excluded_ids)
    qs = qs.order_by("-date_published")[:10]
    return JsonResponse([{"id": a.id, "headline": a.headline} for a in qs], safe=False)


@never_cache
@staff_member_required
def preview_layout(request, layout_id):
    """Render the home template for a specific layout (opens in new tab from admin)."""
    layout = get_object_or_404(HomeLayout, pk=layout_id)
    grid_data = layout.grid_data if isinstance(layout.grid_data, dict) else {}
    return render(request, "homev4/home.html", {
        "layout": layout,
        "publication": layout.publication,
        "home_data": build_home_data(grid_data, publication=layout.publication),
    })


def build_home_data(grid_data, publication=None):
    """
    Pre-fetch all data needed to render the home template from grid_data.
    Returns a single dict with everything ready — the template should not
    need to hit the database or do any lookups.

    Keys returned:
      principal_active (bool), principal_articles (list of Article),
      suplemento_active (bool), suplemento_articles (list of Article),
      especial_active (bool), especial_articles (list of Article),
      sections: list of dicts — only active ones — each with:
        {type, id, slug, name, row, url, articles}
      componentes: list of dicts — only active ones — each with:
        {key, label, description, articles}
    """
    result = {
        "principal_active": False,
        "principal_articles": [],
        "suplemento_active": False,
        "suplemento_articles": [],
        "especial_active": False,
        "especial_articles": [],
        "sections": [],
        "componentes": [],
    }

    _tb = time.perf_counter()
    edition = get_current_edition(publication=publication)

    # PRINCIPAL
    principal_data = grid_data.get("principal") or {}
    result["principal_active"] = _block_active("principal", principal_data.get("active", True))
    db_articles = list(edition.top_articles) if edition else []
    saved_ids = principal_data.get("article_ids", [])
    if saved_ids:
        by_id = {a.id: a for a in db_articles}
        extra_ids = [aid for aid in saved_ids if aid not in by_id]
        if extra_ids:
            # select_related so is_restricted() does not trigger lazy loads per article
            by_id.update({
                a.id: a for a in Article.published.filter(id__in=extra_ids).select_related(
                    _ARTICLE_AUTH_SELECT_RELATED
                )
            })
        result["principal_articles"] = [by_id[aid] for aid in saved_ids if aid in by_id]
    else:
        result["principal_articles"] = db_articles

    logger.warning("  build: principal=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()
    # SUPLEMENTO
    suplemento_data = grid_data.get("suplemento", {})
    result["suplemento_active"] = _block_active("suplemento", suplemento_data.get("active", True))
    if result["suplemento_active"]:
        try:
            result["suplemento_articles"] = _fetch_suplemento_articles(suplemento_data.get("article_ids", []))
        except Exception:
            result["suplemento_articles"] = []

    logger.warning("  build: suplemento=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()
    # ESPECIAL
    especial_data = grid_data.get("especial", {})
    result["especial_active"] = _block_active("especial", especial_data.get("active", True))
    if result["especial_active"]:
        especial_ids = especial_data.get("article_ids", [])
        if especial_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=especial_ids)}
            result["especial_articles"] = [by_id[aid] for aid in especial_ids if aid in by_id]

    logger.warning("  build: especial=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()
    # ÁREAS Y PUBLICACIONES — source of truth is grid_data["sections"] merged with _DEFAULT_AREAS.
    # Areas in _DEFAULT_AREAS not yet in grid_data are appended automatically (same as components).
    # Blocks whose (type, slug) matches today's SUPLEMENTO source are hidden (shown there instead).
    _today_suplemento_source = _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(datetime.date.today().weekday())
    _saved_areas = grid_data.get("sections", [])
    _saved_area_keys = {(s.get("type"), s.get("slug")) for s in _saved_areas}
    _merged_areas = list(_saved_areas) + [
        {"type": a["type"], "slug": a["slug"], "name": a["name"], "active": True, "article_ids": []}
        for a in _DEFAULT_AREAS if (a["type"], a["slug"]) not in _saved_area_keys
    ]
    for _area in _merged_areas:
        if not _area.get("active", True):
            continue
        _area_type = _area.get("type", "section")
        _area_slug = _area.get("slug", "")
        if not _area_slug:
            continue
        # Skip if this area is the current SUPLEMENTO source for today
        if _today_suplemento_source and (_area_type, _area_slug) == _today_suplemento_source:
            continue
        _saved_ids = _area.get("article_ids", [])
        result["sections"].append({
            "type": _area_type,
            "slug": _area_slug,
            "name": _area.get("name", _area_slug),
            "articles": _fetch_area_articles(_area_type, _area_slug, _saved_ids),
        })

    logger.warning("  build: sections=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()
    # COMPONENTES — active ones only, enriched with label, description and articles
    for item in grid_data.get("componentes", []):
        if not item.get("active", True):
            continue
        key = item.get("key", "")
        defn = _COMP_DEF_MAP.get(key, {})
        result["componentes"].append({
            "key": key,
            "label": defn.get("label", key),
            "description": defn.get("description", ""),
            "articles": _fetch_component_articles(key, saved_ids=item.get("article_ids", [])),
        })

    logger.warning("  build: componentes=%.1f ms", (time.perf_counter() - _tb) * 1000)
    return result


# Source to load for SUPLEMENTO when no articles are manually picked.
# Keys are Python weekday integers: 0=Monday, 1=Tuesday, ..., 6=Sunday.
# Values are tuples: ("publication", slug) or ("category", slug).
# Days not listed → SUPLEMENTO stays empty.
_SUPLEMENTO_SOURCE_BY_WEEKDAY = {
    0: ("publication", "deporte"),   # Monday / Lunes
    2: ("category", "mundo"),        # Wednesday / Miércoles
    3: ("publication", "economia"),  # Thursday / Jueves
    4: ("category", "cultura"),      # Friday / Viernes
}

# Default area blocks for ÁREAS Y PUBLICACIONES.
# Each entry defines the source for one block: type + slug.
# "local" is a special type: fetches 1 article from "colonia" + 1 from "maldonado".
_DEFAULT_AREAS = [
    {"type": "category",    "slug": "mundo",      "name": "Mundo"},
    {"type": "category",    "slug": "cultura",    "name": "Cultura"},
    {"type": "local",       "slug": "local",      "name": "Local"},
    {"type": "publication", "slug": "deporte",    "name": "Deporte"},
    {"type": "publication", "slug": "ambiente",   "name": "Ambiente"},
    {"type": "publication", "slug": "economia",   "name": "Economía"},
    {"type": "publication", "slug": "justicia",   "name": "Justicia"},
    {"type": "publication", "slug": "trabajo",    "name": "Trabajo"},
    {"type": "publication", "slug": "salud",      "name": "Salud"},
    {"type": "publication", "slug": "educacion",  "name": "Educación"},
    {"type": "publication", "slug": "feminismos", "name": "Feminismos"},
    {"type": "publication", "slug": "ciencia",    "name": "Ciencia"},
]


def _fetch_source_articles(source_type, slug, limit):
    """Fetch up to `limit` articles from a publication or category source.
    Shared by SUPLEMENTO and ÁREAS — same fetch logic, different limits.
    """
    try:
        if source_type == "publication":
            publication = Publication.objects.get(slug=slug)
            edition = publication.latest_edition()
            if edition:
                return list(edition.top_articles[:limit])
        elif source_type == "category":
            category = Category.objects.get(slug=slug)
            return list(category.home.articles_ordered()[:limit])
    except (Publication.DoesNotExist, Category.DoesNotExist, AttributeError):
        pass
    except Exception as e:
        logger.warning("_fetch_source_articles(%s, %s): %s: %s", source_type, slug, type(e).__name__, e)
    return []


def _fetch_suplemento_articles(saved_ids):
    """Return SUPLEMENTO articles.
    Priority: saved_ids (manually picked via picker).
    Fallback: up to 7 articles from the publication or category mapped to today's weekday.
    """
    if saved_ids:
        by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
        return [by_id[aid] for aid in saved_ids if aid in by_id]
    source = _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(datetime.date.today().weekday())
    if source:
        return _fetch_source_articles(source[0], source[1], limit=7)
    return []


def _fetch_area_articles(area_type, slug, saved_ids):
    """Return articles for an ÁREAS Y PUBLICACIONES block (max 2).
    Priority: saved_ids (manually picked via picker).
    Fallback: 2 articles from the category or publication.
    Special case "local": 1 article from "colonia" + 1 from "maldonado".
    """
    if saved_ids:
        by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
        return [by_id[aid] for aid in saved_ids if aid in by_id]
    if area_type == "local":
        articles = []
        for cat_slug in ("colonia", "maldonado"):
            articles.extend(_fetch_source_articles("category", cat_slug, limit=1))
        return articles
    return _fetch_source_articles(area_type, slug, limit=2)


# Components whose order is always automatic — saved_ids are ignored for these.
_COMPONENTS_AUTO_ORDER = {"lo_ultimo", "lo_mas_leido", "apuntes_del_dia", "radio"}



def _fetch_component_articles(key, saved_ids=None):
    """
    Return the article list for a given component key.
    For components not in _COMPONENTS_AUTO_ORDER, saved_ids are used to
    restore the editorial order (same merge logic as PRINCIPAL).

    Slugs configurable via settings:
      HOMEV4_OPINION_CATEGORY_SLUG   (default: "opinion")
      HOMEV4_APUNTES_SECTION_SLUG    (default: "apuntes-del-dia")
    """
    if key == "lo_ultimo":
        return list(Article.published.order_by("-date_published")[:3])

    if key == "lo_mas_leido":
        # days=1 → day__gt=yesterday → effectively today only
        try:
            return mas_leidos(days=1, limit=5)
        except Exception:
            logger.exception("_fetch_component_articles: lo_mas_leido failed")
            return []

    if key == "opinion":
        if saved_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
            return [by_id[aid] for aid in saved_ids if aid in by_id]
        slug = getattr(settings, "HOMEV4_OPINION_CATEGORY_SLUG", "opinion")
        try:
            category = Category.objects.get(slug=slug)
            if hasattr(category, "home"):
                return list(category.home.articles_ordered()[:2])
        except Category.DoesNotExist:
            logger.warning("_fetch_component_articles: opinion category slug=%r not found", slug)
        return []

    if key == "apuntes_del_dia":
        slug = getattr(settings, "HOMEV4_APUNTES_SECTION_SLUG", "apuntes-del-dia")
        try:
            section = Section.objects.get(slug=slug)
            return list(section.latest(limit=1))
        except Section.DoesNotExist:
            logger.warning("_fetch_component_articles: apuntes section slug=%r not found", slug)
        return []

    # recomendadas_lv, recomendadas_domingo: fully manual — only saved articles are shown
    if key in ("recomendadas_lv", "recomendadas_domingo"):
        if saved_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
            return [by_id[aid] for aid in saved_ids if aid in by_id]
        return []

    if key in ("le_monde", "lento"):
        pub_slug = "le-monde-diplomatique" if key == "le_monde" else "lento"
        if saved_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids)}
            return [by_id[aid] for aid in saved_ids if aid in by_id]
        return _fetch_source_articles("publication", pub_slug, limit=2)

    # radio: no articles, just a visibility toggle in the layout editor
    # newsletter_dia: pending implementation
    return []


def _add_auth_context(context, user, articles):
    """
    Populate restricteds, restricteds_allowed, follows in context.
    Mirrors homev3's ctx_update_article_extradata logic.
    articles: flat list of all Article objects visible in the home for this user.
    """
    user_has_subscriber = hasattr(user, "subscriber")
    follow_set = set(
        user.follow_set.filter(
            content_type=ContentType.objects.get_for_model(Article)
        ).values_list("object_id", flat=True)
    )
    for a in articles:
        if not a:
            continue
        compute_follow = True
        a_id = a.id
        if a.is_restricted(True):
            context["restricteds"].append(a_id)
            compute_follow = (
                user_has_subscriber
                and user.subscriber.is_subscriber(a.main_section.edition.publication.slug)
            )
            if compute_follow:
                context["restricteds_allowed"].append(a_id)
        if compute_follow and str(a_id) in follow_set:
            context["follows"].append(a_id)


@_log_timing
@decorate_if_auth(decorator=never_cache)
@decorate_if_no_auth(decorator=vary_on_cookie)
@decorate_if_no_auth(decorator=cache_control(no_cache=True, no_store=True, must_revalidate=True, max_age=_cache_maxage))
def active_layout(request, publication_slug=None):
    # Resolve publication: explicit slug in URL or the default one from settings.
    if publication_slug:
        publication = get_object_or_404(Publication, slug=publication_slug)
    else:
        publication = get_default_publication()

    # Get the layout that should be active right now for this publication.
    # get_active_layout() checks manual overrides first, then day/time schedules.
    # Returns None if no layout matches — build_home_data handles the empty dict gracefully.
    layout = HomeLayout.get_active_layout(publication)
    grid_data = layout.grid_data if (layout and isinstance(layout.grid_data, dict)) else {}

    # Pre-fetch all content defined by the layout editor into a single dict.
    # The template only reads from home_data — no DB calls inside the template.
    _t0 = time.perf_counter()
    home_data = build_home_data(grid_data, publication=publication)
    logger.warning("active_layout build_home_data: %.1f ms", (time.perf_counter() - _t0) * 1000)
    context = {
        "layout": layout,
        "publication": publication,
        "home_data": home_data,
    }

    # Each publication can store arbitrary extra template vars in its extra_context
    # JSONField (e.g. custom flags or URLs specific to that publication).
    if isinstance(getattr(publication, "extra_context", None), dict):
        context.update(publication.extra_context)

    user = request.user
    if user.is_authenticated:
        # Initialize the three auth lists the base template reads to decide
        # what to show/hide per article (paywall lock, follow indicator, etc.).
        context.update({"restricteds": [], "restricteds_allowed": [], "follows": []})

        # Flatten all articles visible in the home so we can evaluate each one.
        # Principal articles + all active section articles are included.
        # Component articles are not yet included (pending data source implementation).
        #
        # top_articles uses prefetch_related from the ArticleRel perspective, which does
        # not populate main_section cache on Article instances for direct access.
        # Re-fetch principal articles by ID with select_related so is_restricted()
        # does not trigger lazy loads per article.
        principal_ids = [a.id for a in home_data.get("principal_articles", [])]
        if principal_ids:
            principal_by_id = {
                a.id: a for a in Article.published.filter(id__in=principal_ids).select_related(
                    _ARTICLE_AUTH_SELECT_RELATED
                )
            }
            all_articles = [principal_by_id[aid] for aid in principal_ids if aid in principal_by_id]
        else:
            all_articles = []
        for sec in home_data.get("sections", []):
            all_articles.extend(sec.get("articles", []))

        # Populate restricteds / restricteds_allowed / follows in context.
        _t1 = time.perf_counter()
        _add_auth_context(context, user, all_articles)
        logger.warning("active_layout _add_auth_context: %.1f ms", (time.perf_counter() - _t1) * 1000)
        # Unsubscribed newsletters banner: show only if the feature is enabled,
        # the user has a subscriber profile with an email, and hasn't closed it yet.
        if (
            getattr(settings, "HOMEV3_NEWSLETTERS_HEADER_ENABLED", False)
            and hasattr(user, "subscriber")
            and user.email
            and not request.session.get("unsubscribed_nls_notice_closed")
        ):
            context["unsubscribed_newsletters"] = unsubscribed_newsletters(user.subscriber)

    _t2 = time.perf_counter()
    response = render(request, "homev4/home.html", context)
    logger.warning("active_layout render: %.1f ms", (time.perf_counter() - _t2) * 1000)
    return response
