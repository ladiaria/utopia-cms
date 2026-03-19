import datetime
import json
import logging
import time

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
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
_DEFAULT_SIDEBAR_COMPONENT_TEMPLATE = "homev4/sidebar_components/default.html"
_HOME_TEMPLATE = "homev4/home.html"


def _resolve_sidebar_template(key):
    candidate = f"homev4/sidebar_components/{key}.html"
    try:
        get_template(candidate)
        return candidate
    except TemplateDoesNotExist:
        return _DEFAULT_SIDEBAR_COMPONENT_TEMPLATE

COMPONENT_DEFINITIONS = [
    {"key": "apuntes_del_dia",      "label": "Apuntes del día",          "description": "",                "sortable_articles": False},
    {"key": "opinion",              "label": "Opinión",                  "description": "Área",            "has_picker": True},
    {"key": "lo_ultimo",            "label": "Lo último",                "description": "3PM a 6AM",       "sortable_articles": False},
    {"key": "radio",                "label": "Radio",                    "description": ""},
    {"key": "recomendadas_lv",      "label": "Recomendadas",             "description": "Lunes a viernes", "has_picker": True},
    {"key": "newsletter_dia",       "label": "Newsletter del día",       "description": ""},
    {"key": "recomendadas_domingo", "label": "Recomendadas Domingo",     "description": "Los domingos",    "has_picker": True},
    {"key": "lo_mas_leido",         "label": "Lo más leído hoy",         "description": "",                "sortable_articles": False},
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


@staff_member_required
def article_search(request):
    """Return up to 10 published articles matching the ?q= headline search (for the picker widget)."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    qs = Article.published.filter(headline__icontains=q).order_by("-date_published")[:10]
    return JsonResponse([{"id": a.id, "headline": a.headline} for a in qs], safe=False)


@never_cache
@staff_member_required
def preview_layout(request, layout_id):
    """Render the home template for a specific layout (opens in new tab from admin)."""
    layout = get_object_or_404(HomeLayout, pk=layout_id)
    grid_data = layout.grid_data if isinstance(layout.grid_data, dict) else {}
    home_template = getattr(settings, "HOMEV4_HOME_TEMPLATE", _HOME_TEMPLATE)
    return render(request, home_template, {
        "layout": layout,
        "publication": layout.publication,
        "home_data": build_home_data(grid_data, publication=layout.publication),
        "is_portada": True,
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
        ordered = [by_id[aid] for aid in saved_ids if aid in by_id]
        saved_set = set(saved_ids)
        for a in db_articles:
            if a.id not in saved_set:
                ordered.append(a)
        result["principal_articles"] = ordered
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
    # SECTIONS — source of truth is Section.objects.filter(in_home=True), ordered by home_order.
    # grid_data["sections"] provides per-section overrides only: active state and article_ids (picker).
    # This mirrors how PRINCIPAL works: the DB defines what appears, grid_data only adjusts it.
    # Two-pass strategy to avoid N Article queries (one per section):
    #   Pass 1: iterate live DB sections, collect ordered article IDs per section
    #           (section.latest() uses raw SQL — unavoidable one query per section).
    #   Pass 2: single bulk Article.published.filter(id__in=all_ids).select_related(...)
    #           replaces the N individual re-fetch queries.
    _saved_sec_overrides = {s["slug"]: s for s in grid_data.get("sections", []) if s.get("slug")}
    _db_sections = list(Section.objects.filter(in_home=True).order_by("home_order"))

    # Pass 1
    _sec_entries = []
    for _section in _db_sections:
        _override = _saved_sec_overrides.get(_section.slug, {})
        if not _override.get("active", True):
            continue
        _saved_ids = _override.get("article_ids", [])
        _ordered_ids = _saved_ids if _saved_ids else [a.id for a in _section.latest(limit=2)]
        _sec_entries.append((_section, _ordered_ids))

    # Pass 2: single bulk Article fetch for all sections combined
    _all_sec_article_ids = {aid for _, ids in _sec_entries for aid in ids}
    _sec_articles_by_id = (
        {a.id: a for a in Article.published.filter(id__in=_all_sec_article_ids).select_related(
            _ARTICLE_AUTH_SELECT_RELATED
        )}
        if _all_sec_article_ids else {}
    )

    for _section, _ordered_ids in _sec_entries:
        result["sections"].append({
            "type": "section",
            "id": _section.pk,
            "slug": _section.slug,
            "name": _section.name,
            "url": _section.get_absolute_url(),
            "articles": [_sec_articles_by_id[aid] for aid in _ordered_ids if aid in _sec_articles_by_id],
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
            "sidebar_component_template": _resolve_sidebar_template(key),
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
        source_type, slug = source
        try:
            if source_type == "publication":
                publication = Publication.objects.get(slug=slug)
                edition = publication.latest_edition()
                if edition:
                    return list(edition.top_articles[:7])
            elif source_type == "category":
                category = Category.objects.get(slug=slug)
                return list(category.home.articles_ordered()[:7])
        except (Publication.DoesNotExist, Category.DoesNotExist, AttributeError):
            pass
    return []


# Components whose order is always automatic — saved_ids are ignored for these.
_COMPONENTS_AUTO_ORDER = {"lo_ultimo", "lo_mas_leido", "apuntes_del_dia", "radio"}


def _merge_article_order(db_articles, saved_ids):
    """
    Return db_articles reordered according to saved_ids, with any new DB
    articles not in saved_ids appended at the end. Same logic as PRINCIPAL.
    """
    if not saved_ids:
        return db_articles
    db_by_id = {a.id: a for a in db_articles}
    ordered = [db_by_id[aid] for aid in saved_ids if aid in db_by_id]
    saved_set = set(saved_ids)
    for a in db_articles:
        if a.id not in saved_set:
            ordered.append(a)
    return ordered


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
        "is_portada": True,
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

    home_template = getattr(settings, "HOMEV4_HOME_TEMPLATE", _HOME_TEMPLATE)
    _t2 = time.perf_counter()
    response = render(request, home_template, context)
    logger.warning("active_layout render: %.1f ms", (time.perf_counter() - _t2) * 1000)
    return response
