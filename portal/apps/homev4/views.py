import copy
import datetime
import json
import logging
import time

from django.db import transaction
from django.utils import timezone
from django.utils.formats import date_format

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
from django.core.cache import cache
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.vary import vary_on_cookie

from core.models import Article, ArticleRel, Edition, Publication, Section, Category, get_current_edition
from core.views.masleidos import mas_leidos
from thedaily.utils import unsubscribed_newsletters

from decorators import decorate_if_no_auth, decorate_if_auth

from .models import HomeLayout

logger = logging.getLogger("homev4")

_cache_maxage = getattr(settings, "HOMEV3_INDEX_CACHE_MAXAGE", 120)

# Newsletters auto-activated on registration — excluded from the newsletter_dia picker.
_MASIVA_NEWSLETTER_SLUGS = frozenset([
    ("publication", "ladiaria"),     # A la mañana
    ("category",    "tarde"),        # A la tarde
    ("publication", "findesemana"),  # Fin de semana
    ("category",    "semanal"),      # Resumen semanal
])


def _log_timing(view_func):
    def wrapper(request, *args, **kwargs):
        t0 = time.perf_counter()
        response = view_func(request, *args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.warning("active_layout timing: %.1f ms (user_auth=%s)", elapsed, request.user.is_authenticated)
        return response
    wrapper.__name__ = view_func.__name__
    return wrapper

# select_related chains and prefetch targets for all article queries on the home.
# Ensures template and auth checks don't trigger lazy DB hits per article.
# Update these constants if the Article/ArticleRel model relationships change.
_ARTICLE_AUTH_SELECT_RELATED = (
    "main_section__edition__publication",
    "main_section__section",
    # render_hierarchy accesses section.category per article — pre-load to avoid N+1
    "main_section__section__category",
)
_ARTICLE_PREFETCH_RELATED = ("photo__extended__photographer", "byline")
# Extra prefetch names specific to the deployment (e.g. "verifica_check_option" for ladiaria).
# Configured via HOMEV4_ARTICLE_EXTRA_PREFETCH in local settings.
_ARTICLE_EXTRA_PREFETCH = tuple(getattr(settings, 'HOMEV4_ARTICLE_EXTRA_PREFETCH', ()))


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
_DEFAULT_SECTION_TEMPLATE = "homev4/sections/default.html"
_HOME_TEMPLATE = "homev4/home.html"


def _resolve_sidebar_template(key):
    candidate = f"homev4/sidebar_components/{key}.html"
    try:
        get_template(candidate)
        return candidate
    except TemplateDoesNotExist:
        return _DEFAULT_SIDEBAR_COMPONENT_TEMPLATE


def _resolve_section_template(slug):
    candidate = f"homev4/sections/{slug}.html"
    try:
        get_template(candidate)
        return candidate
    except TemplateDoesNotExist:
        return _DEFAULT_SECTION_TEMPLATE

COMPONENT_DEFINITIONS = [
    {"key": "apuntes_del_dia",      "label": "Apuntes del día",          "description": "",                "sortable_articles": False},
    {"key": "opinion",              "label": "Opinión",                  "description": "Área",            "has_picker": True},
    {"key": "lo_ultimo",            "label": "Lo último",                "description": "3PM a 6AM",       "has_picker": True, "pin_mode": True, "sortable_articles": True},
    {"key": "radio",                "label": "Radio",                    "description": "",                "no_articles": True},
    {"key": "recomendadas_lv",      "label": "Recomendadas",             "description": "Lunes a sábado",  "has_picker": True},
    {"key": "newsletter_dia",       "label": "Newsletter del día",       "description": "",                "newsletter_mode": True},
    {"key": "recomendadas_domingo", "label": "Recomendadas Domingo",     "description": "Los domingos",    "has_picker": True},
    {"key": "edicion_del_dia",      "label": "Edición del día",          "description": "",                "no_articles": True},
    {"key": "lo_mas_leido",         "label": "Lo más leído hoy",         "description": "",                "sortable_articles": False},
    {"key": "le_monde",             "label": "Le Monde Diplomatique",    "description": "",                "has_picker": True},
    {"key": "lento",                "label": "Lento",                    "description": "",                "has_picker": True},
    {"key": "humor",                "label": "Humor",                    "description": "",                "replace_mode": True},
    {"key": "crucigrama",           "label": "Crucigrama",               "description": "",                "no_articles": True},
]

_COMP_DEF_MAP = {d["key"]: d for d in COMPONENT_DEFINITIONS}

DEFAULT_COMPONENTES = [{"key": d["key"], "active": True} for d in COMPONENT_DEFINITIONS]

# Maximum article_ids per block — enforced in save_grid (backend) and mirrored in the picker (frontend).
# "area" applies to every section in the sections list.
BLOCK_ARTICLE_LIMITS = {
    "principal":           10,
    "suplemento":           7,
    "especial":             1,
    "area":                 2,
    "apuntes_del_dia":      1,
    "opinion":              3,
    "recomendadas_lv":      4,
    "recomendadas_domingo": 4,
    "le_monde":             2,
    "lento":                2,
    "humor":                1,
}

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


_PAPEL_CACHE_KEY = "homev4:papel_url"

_PAPEL_DAY_NAMES = {0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves", 4: "viernes", 5: "sabado", 6: "domingo"}


def _get_papel_edition():
    """Return the Edition to use for papel URL and cover: today's or most recent with PDF."""
    today = timezone.localdate()
    publication = get_default_publication()
    if today.weekday() >= 5:
        # On weekends ladiaria does not publish — use the most recent findesemana edition with PDF.
        fds_pub = Publication.objects.filter(slug="findesemana").first()
        return (
            Edition.objects.filter(publication=fds_pub).exclude(pdf="").order_by("-date_published").first()
            if fds_pub else None
        ) or Edition.objects.filter(publication=publication).exclude(pdf="").order_by("-date_published").first()
    else:
        # On weekdays prefer today's ladiaria edition; fall back to the most recent one with PDF.
        return (
            Edition.objects.filter(publication=publication, date_published=today).exclude(pdf="").first()
            or Edition.objects.filter(publication=publication).exclude(pdf="").order_by("-date_published").first()
        )


def get_papel_url():
    """
    Returns the URL for today's papel edition (or the most recent one with a PDF).
    Reads from cache; on miss, queries Edition, saves to cache, and returns the URL.
    Falls back to settings.PAPEL_FALLBACK_URL if no edition with PDF is found or on error.
    """
    cached = cache.get(_PAPEL_CACHE_KEY)
    if cached:
        return cached

    try:
        edition = _get_papel_edition()
        if not edition:
            return settings.PAPEL_FALLBACK_URL
        url = (
            "https://papel.ladiaria.com.uy/reader/"
            f"la-diaria-{_PAPEL_DAY_NAMES[edition.date_published.weekday()]}-"
            f"{edition.date_published.strftime('%d%m%Y')}?location=1"
        )
        try:
            cache.set(_PAPEL_CACHE_KEY, url)
        except Exception:
            pass
        return url
    except Exception:
        return settings.PAPEL_FALLBACK_URL



def _propagate_article_ids(source_layout, source_grid):
    """
    Copy article_ids from source_grid to all other layouts of the same publication.
    Active/inactive flags in each target layout are preserved.
    Called after save_grid so that all layouts stay in sync.
    """
    others = list(
        HomeLayout.objects.select_for_update()
        .exclude(pk=source_layout.pk)
        .filter(publication=source_layout.publication)
    )
    if not others:
        return

    src_top = {
        block: source_grid.get(block, {}).get("article_ids", [])
        for block in ("principal", "suplemento", "especial", "extra_articles")
    }
    src_sections = {s["slug"]: s.get("article_ids", []) for s in source_grid.get("sections", [])}
    # Exclude no_articles components (e.g. crucigrama) — they have no article_ids to propagate.
    src_componentes = {
        c["key"]: c.get("article_ids", [])
        for c in source_grid.get("componentes", [])
        if not _COMP_DEF_MAP.get(c.get("key", ""), {}).get("no_articles")
    }
    # None means absent (delete from siblings); a dict means create/update in siblings.
    src_se = source_grid.get("suplemento_extra")

    now = timezone.now()
    old_grids = {}
    for layout in others:
        old_grids[layout.pk] = layout.grid_data if isinstance(layout.grid_data, dict) else {}
        # Deep copy so mutations to gd's nested dicts do not corrupt old_grids,
        # which is used later as the "before" state in _write_audit_log.
        gd = copy.deepcopy(old_grids[layout.pk])

        for block, ids in src_top.items():
            block_data = gd.get(block) if isinstance(gd.get(block), dict) else {}
            block_data["article_ids"] = ids
            gd[block] = block_data

        for sec in gd.get("sections", []):
            if sec.get("slug") in src_sections:
                sec["article_ids"] = src_sections[sec["slug"]]

        existing_comp_keys = {c.get("key") for c in gd.get("componentes", [])}
        for comp in gd.get("componentes", []):
            if comp.get("key") in src_componentes:
                comp["article_ids"] = src_componentes[comp["key"]]
        # Add component entries that exist in source but are absent in the sibling
        # (e.g. layouts created before a new component was added to COMPONENT_DEFINITIONS).
        for key, ids in src_componentes.items():
            if key not in existing_comp_keys:
                gd.setdefault("componentes", []).append({"key": key, "active": True, "article_ids": ids})

        # SUPLEMENTO_EXTRA: propagate as a full block (create / update / delete)
        if src_se is not None:
            existing_se = gd.get("suplemento_extra")
            if not isinstance(existing_se, dict):
                # Sibling has no block yet — copy full block from source (including source fields).
                gd["suplemento_extra"] = dict(src_se)
            else:
                # article_ids and active propagate so enabling/disabling in one layout syncs all.
                # source_type and source_slug are per-layout metadata and are intentionally preserved.
                existing_se["article_ids"] = list(src_se.get("article_ids", []))
                existing_se["active"] = src_se.get("active", True)
        else:
            # Source removed suplemento_extra — sync siblings (delete the block).
            gd.pop("suplemento_extra", None)

        layout.grid_data = gd
        layout.modified = now

    HomeLayout.objects.bulk_update(others, ["grid_data", "modified"])
    # Audit each propagated layout separately so the log shows which sibling layouts
    # were affected and what changed, distinguishable from the source layout's own entry.
    for layout in others:
        _write_audit_log(layout, old_grids[layout.pk], layout.grid_data, "propagation")
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


def _write_audit_log(layout, old_grid, new_grid, triggered_by, user=None):
    """Write one AuditLog entry per block whose article_ids changed between old_grid and new_grid.
    All entries from a single call share the same save_id so they can be grouped.
    """
    import uuid
    from .models import HomeLayoutAuditLog
    old_grid = old_grid if isinstance(old_grid, dict) else {}
    new_grid = new_grid if isinstance(new_grid, dict) else {}
    entries = []
    save_id = uuid.uuid4()

    for block in ("principal", "suplemento", "especial", "extra_articles", "suplemento_extra"):
        before = list(old_grid.get(block, {}).get("article_ids", []))
        after = list(new_grid.get(block, {}).get("article_ids", []))
        if before != after:
            entries.append(HomeLayoutAuditLog(layout=layout, save_id=save_id, triggered_by=triggered_by, user=user, block_key=block, ids_before=before, ids_after=after))

    old_secs = {s["slug"]: list(s.get("article_ids", [])) for s in old_grid.get("sections", []) if s.get("slug")}
    new_secs = {s["slug"]: list(s.get("article_ids", [])) for s in new_grid.get("sections", []) if s.get("slug")}
    for slug in sorted(set(old_secs) | set(new_secs)):
        before = old_secs.get(slug, [])
        after = new_secs.get(slug, [])
        if before != after:
            entries.append(HomeLayoutAuditLog(layout=layout, save_id=save_id, triggered_by=triggered_by, user=user, block_key="sections:" + slug, ids_before=before, ids_after=after))

    old_comps = {c["key"]: list(c.get("article_ids", [])) for c in old_grid.get("componentes", []) if c.get("key")}
    new_comps = {c["key"]: list(c.get("article_ids", [])) for c in new_grid.get("componentes", []) if c.get("key")}
    for key in sorted(set(old_comps) | set(new_comps)):
        before = old_comps.get(key, [])
        after = new_comps.get(key, [])
        if before != after:
            entries.append(HomeLayoutAuditLog(layout=layout, save_id=save_id, triggered_by=triggered_by, user=user, block_key="componentes:" + key, ids_before=before, ids_after=after))

    if entries:
        HomeLayoutAuditLog.objects.bulk_create(entries)


def _sync_principal_to_edition(old_ids, new_ids, layout, user):
    """Sync ArticleRel home_top/top_position to match the editor's changes to the principal block.
    Prevents celery:refresh from reinserting articles the editor removed or reordered, since refresh
    uses Edition.top_articles (filtered by home_top=True, ordered by top_position) as its source.
    """
    if old_ids == new_ids:
        return
    # On weekends the active edition belongs to "findesemana", not the layout's publication.
    # Mirror the same weekday logic used in refresh_home_layouts_task so both functions
    # operate on the same edition.
    weekday = timezone.localdate().weekday()
    if weekday >= 5:
        fds_pub = Publication.objects.filter(slug="findesemana").first()
        edition = get_current_edition(publication=fds_pub) if fds_pub else get_current_edition(publication=layout.publication)
    else:
        edition = get_current_edition(publication=layout.publication)
    if edition is None:
        return

    removed_ids = set(old_ids) - set(new_ids)
    if removed_ids:
        # Clear cover flag so celery:refresh won't see them in Edition.top_articles
        ArticleRel.objects.filter(
            edition=edition, article_id__in=removed_ids, home_top=True
        ).update(home_top=False, top_position=None)

    added_ids = set(new_ids) - set(old_ids)
    edition_article_ids = set(edition.articlerel_set.values_list("article_id", flat=True))
    for idx, article_id in enumerate(new_ids):
        if article_id in added_ids and article_id in edition_article_ids:
            # Article newly added to principal and belongs to today's edition:
            # enable cover flag on the row that belongs to this edition (one row per section,
            # pick the one with the lowest position to avoid enabling a secondary-section row).
            first_rel = ArticleRel.objects.filter(
                edition=edition, article_id=article_id,
            ).order_by("position").first()
            if first_rel:
                first_rel.home_top = True
                first_rel.top_position = idx + 1
                first_rel.save(update_fields=["home_top", "top_position"])
        elif article_id in added_ids:
            # Article added via picker but not yet in this edition — create an ArticleRel so
            # celery:refresh can see it in Edition.top_articles and the principal order is preserved.
            try:
                article = Article.objects.get(pk=article_id)
                section = article.main_section.section if article.main_section_id else None
                if section:
                    ArticleRel.objects.create(
                        edition=edition,
                        article=article,
                        section=section,
                        position=1,
                        home_top=True,
                        top_position=idx + 1,
                    )
            except Article.DoesNotExist:
                pass
        elif article_id not in added_ids:
            # Align top_position with the new principal order.
            # Filter by home_top=True to avoid accidentally setting top_position on
            # secondary-section rows of articles that appear in multiple sections.
            ArticleRel.objects.filter(
                edition=edition, article_id=article_id, home_top=True
            ).update(top_position=idx + 1)

    _write_audit_log(
        layout,
        {"principal": {"article_ids": list(old_ids)}},
        {"principal": {"article_ids": list(new_ids)}},
        "editor:edition_sync",
        user=user,
    )


@staff_member_required
def save_grid(request, layout_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    layout = get_object_or_404(HomeLayout, pk=layout_id)
    try:
        data = json.loads(request.body)
        grid_data = data.get("grid_data", {})
        # Enforce per-block article_ids limits — violating these breaks deduplication logic.
        for block in ("principal", "suplemento", "especial"):
            ids = grid_data.get(block, {}).get("article_ids", [])
            limit = BLOCK_ARTICLE_LIMITS[block]
            if len(ids) > limit:
                return JsonResponse({"error": f"{block} cannot have more than {limit} articles"}, status=400)
        area_limit = BLOCK_ARTICLE_LIMITS["area"]
        for section in grid_data.get("sections", []):
            ids = section.get("article_ids", [])
            if len(ids) > area_limit:
                slug = section.get("slug", "?")
                return JsonResponse({"error": f"Area '{slug}' cannot have more than {area_limit} articles"}, status=400)
        for comp in grid_data.get("componentes", []):
            key = comp.get("key", "")
            limit = BLOCK_ARTICLE_LIMITS.get(key)
            if limit and len(comp.get("article_ids", [])) > limit:
                return JsonResponse({"error": f"Component '{key}' cannot have more than {limit} articles"}, status=400)
        # Strip article_ids from newsletter_mode components — they use newsletter_refs instead.
        for comp in grid_data.get("componentes", []):
            if "newsletter_refs" in comp:
                comp.pop("article_ids", None)
        # Capture state before save so audit log can compute the diff per block.
        old_grid = layout.grid_data if isinstance(layout.grid_data, dict) else {}
        with transaction.atomic():
            layout.grid_data = grid_data
            layout.save()
            # Re-fetch from DB to confirm the save actually persisted
            layout.refresh_from_db(fields=["grid_data"])
            _propagate_article_ids(layout, layout.grid_data)
            _write_audit_log(layout, old_grid, layout.grid_data, "editor", user=request.user)
            # Keep edition ArticleRel in sync with editor's principal changes so celery:refresh doesn't revert them
            old_principal_ids = old_grid.get("principal", {}).get("article_ids", [])
            new_principal_ids = layout.grid_data.get("principal", {}).get("article_ids", [])
            _sync_principal_to_edition(old_principal_ids, new_principal_ids, layout, request.user)
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
        # Keep the preview session in sync with the saved state so that
        # refreshing /?preview=1 reflects the just-saved grid without
        # requiring the editor to click "Vista previa" again.
        request.session["preview_grid_data"] = layout.grid_data
        request.session["preview_grid_saved"] = True

        # Sync RadioGeneralConfig.show_banner when the editor toggles the radio block.
        # Uses .update() (no signals) to avoid triggering the post_save cycle.
        old_radio = next((c.get("active", True) for c in old_grid.get("componentes", []) if c.get("key") == "radio"), None)
        new_radio = next((c.get("active", True) for c in layout.grid_data.get("componentes", []) if c.get("key") == "radio"), None)
        if old_radio is not None and new_radio is not None and old_radio != new_radio:
            try:
                from utopia_cms_radio.models import RadioGeneralConfig
                RadioGeneralConfig.objects.update(show_banner="Y" if new_radio else "N")
            except ImportError:
                pass

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


@never_cache
@staff_member_required
def article_search(request):
    """Return up to 10 published articles matching the ?q= headline search (for the picker widget).
    When the JS editor sends exclude_ids it represents the authoritative live DOM state — use it
    exclusively and skip the DB lookup. Fall back to layout_id DB lookup only when exclude_ids is absent.
    """
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)

    excluded_ids = set()
    if "exclude_ids" in request.GET:
        # JS sends current editor state — authoritative; DB lookup would re-exclude removed articles.
        for raw_id in request.GET["exclude_ids"].split(","):
            try:
                excluded_ids.add(int(raw_id))
            except ValueError:
                pass
    else:
        # No JS state available — fall back to DB to prevent cross-zone duplicates.
        layout_id = request.GET.get("layout_id")
        if layout_id:
            try:
                layout = HomeLayout.objects.get(pk=layout_id)
                gd = layout.grid_data if isinstance(layout.grid_data, dict) else {}
                for block in ("principal", "suplemento", "especial"):
                    block_data = gd.get(block, {})
                    if block_data.get("active", True):
                        excluded_ids.update(block_data.get("article_ids", []))
                for sec in gd.get("sections", []):
                    if sec.get("active", True):
                        excluded_ids.update(sec.get("article_ids", []))
                for comp in gd.get("componentes", []):
                    if comp.get("active", True):
                        excluded_ids.update(comp.get("article_ids", []))
            except HomeLayout.DoesNotExist:
                pass

    qs = Article.published.filter(headline__icontains=q)

    # Optional source filter for suplemento_extra picker: narrow results to publication or category.
    source_type = request.GET.get("source_type", "").strip()
    source_slug = request.GET.get("source_slug", "").strip()
    if source_type == "publication" and source_slug:
        qs = qs.filter(main_section__edition__publication__slug=source_slug)
    elif source_type == "category" and source_slug:
        # home_articles is the related_name on CategoryHomeArticle.article
        qs = qs.filter(home_articles__home__category__slug=source_slug).distinct()

    if excluded_ids:
        qs = qs.exclude(id__in=excluded_ids)
    qs = qs.order_by("-date_published")[:10]
    return JsonResponse([{"id": a.id, "headline": a.headline} for a in qs], safe=False)


@never_cache
@staff_member_required
def lo_ultimo_latest(request, layout_id):
    """Return the resolved lo_ultimo article list for the editor 'replace unpinned' button.

    GET params:
      exclude[]: IDs already placed in principal/suplemento/especial (from editor state).
      pinned[]:  IDs currently pinned in lo_ultimo — kept at their saved position.
      saved[]:   current article_ids order — used to preserve pinned positions in the response.

    Returns {articles: [{id, headline}, ...]} with the full resolved list of up to 3 articles.
    """
    get_object_or_404(HomeLayout, pk=layout_id)
    exclude_ids = {int(x) for x in request.GET.getlist("exclude") if x.isdigit()}
    pinned_ids = {int(x) for x in request.GET.getlist("pinned") if x.isdigit()}
    saved_ids = [int(x) for x in request.GET.getlist("saved") if x.isdigit()]
    articles = _fetch_component_articles(
        "lo_ultimo",
        saved_ids=saved_ids,
        pinned_ids=pinned_ids,
        exclude_ids=exclude_ids,
    )
    return JsonResponse({"articles": [{"id": a.id, "headline": a.headline} for a in articles]})


def _is_tarde_mode(layout):
    """Return True if the layout's start_time is 15:00 or later."""
    return (
        layout is not None
        and layout.start_time is not None
        and layout.start_time >= datetime.time(15, 0)
    )


# Maps layout day codes to Spanish day-name keywords used to filter newsletter_periodicity.
# newsletter_periodicity is a free-text field, so we match substrings case-insensitively.
# Accented and unaccented variants are included to handle inconsistent data entry.
# Multi-day codes (lv, lmjv) expand to all their individual day names so that a newsletter
# published on any of those days is considered a match.
_DAY_CODE_TO_KEYWORDS = {
    "lu":   ["lunes"],
    "ma":   ["martes"],
    "mi":   ["miércoles", "miercoles"],
    "ju":   ["jueves"],
    "vi":   ["viernes"],
    "sa":   ["sábado", "sabado"],
    "do":   ["domingo"],
    "lv":   ["lunes", "viernes"],
    "lmjv": ["lunes", "miércoles", "miercoles", "jueves", "viernes"],
}


@never_cache
@staff_member_required
def newsletter_search(request):
    """Search endpoint for the newsletter_dia picker in the layout editor.

    Returns up to 10 newsletters (Publications + Categories with has_newsletter=True)
    whose name matches ?q= (min 2 chars). Masiva newsletters are always excluded because
    they are auto-activated on registration and should not be manually curated.

    Optional ?day= parameter (layout day code, e.g. "ma", "lu") narrows results to
    newsletters whose newsletter_periodicity field contains any keyword for that day.
    This relies on _DAY_CODE_TO_KEYWORDS and icontains matching — it works as long as
    newsletter_periodicity values consistently include the Spanish day name.

    Response shape: [{type, slug, name, periodicity}, ...]
    """
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    day = request.GET.get("day", "").strip()
    day_keywords = _DAY_CODE_TO_KEYWORDS.get(day, [])
    masiva_pub_slugs = {s for t, s in _MASIVA_NEWSLETTER_SLUGS if t == "publication"}
    masiva_cat_slugs = {s for t, s in _MASIVA_NEWSLETTER_SLUGS if t == "category"}

    def day_filter(qs):
        # If no day is specified (or unrecognized code), return all results unfiltered.
        if not day_keywords:
            return qs
        from django.db.models import Q
        q_day = Q()
        for kw in day_keywords:
            q_day |= Q(newsletter_periodicity__icontains=kw)
        return qs.filter(q_day)

    results = []
    pub_qs = day_filter(Publication.objects.filter(has_newsletter=True, name__icontains=q).exclude(slug__in=masiva_pub_slugs)).order_by("name")[:10]
    for pub in pub_qs:
        # Use newsletter_name (the branded name) over the publication name when available.
        results.append({"type": "publication", "slug": pub.slug, "name": pub.newsletter_name or pub.name, "periodicity": pub.newsletter_periodicity or ""})
    cat_qs = day_filter(Category.objects.filter(has_newsletter=True, name__icontains=q).exclude(slug__in=masiva_cat_slugs)).order_by("name")[:10]
    for cat in cat_qs:
        results.append({"type": "category", "slug": cat.slug, "name": cat.name, "periodicity": cat.newsletter_periodicity or ""})
    results.sort(key=lambda x: x["name"])
    return JsonResponse(results[:10], safe=False)


def _resolve_newsletter_refs(refs):
    """Resolve a list of 'type:slug' strings to newsletter dicts {type, slug, name, periodicity}.

    Used by both build_home_data (to enrich newsletter_dia component data) and
    _build_editor_data in admin.py (to display saved newsletters in the layout editor).
    Masiva newsletters are silently skipped even if somehow saved in grid_data.
    Non-existent slugs are also silently skipped.
    """
    result = []
    masiva_pub_slugs = {s for t, s in _MASIVA_NEWSLETTER_SLUGS if t == "publication"}
    masiva_cat_slugs = {s for t, s in _MASIVA_NEWSLETTER_SLUGS if t == "category"}
    for ref in refs:
        try:
            nl_type, nl_slug = ref.split(":", 1)
        except ValueError:
            continue
        try:
            if nl_type == "publication" and nl_slug not in masiva_pub_slugs:
                obj = Publication.objects.get(slug=nl_slug, has_newsletter=True)
                result.append({"type": "publication", "slug": nl_slug, "name": obj.newsletter_name or obj.name, "periodicity": obj.newsletter_periodicity or "", "tagline": obj.newsletter_tagline or ""})
            elif nl_type == "category" and nl_slug not in masiva_cat_slugs:
                obj = Category.objects.get(slug=nl_slug, has_newsletter=True)
                result.append({"type": "category", "slug": nl_slug, "name": obj.name, "periodicity": obj.newsletter_periodicity or "", "tagline": obj.newsletter_tagline or ""})
        except (Publication.DoesNotExist, Category.DoesNotExist):
            pass
    return result


def _pick_newsletter_dia(newsletters, user):
    """Return the first newsletter in the list that user is not yet subscribed to.

    Falls back to newsletters[0] for unauthenticated users or those without a
    subscriber profile (rules 1 and 2).  Returns None when all newsletters are
    active (rule 4).
    """
    if user.is_authenticated and hasattr(user, "subscriber"):
        sub = user.subscriber
        active_refs = (
            {"publication:" + slug for slug in sub.newsletters.values_list("slug", flat=True)} |
            {"category:" + slug for slug in sub.category_newsletters.values_list("slug", flat=True)}
        )
        for nl in newsletters:
            if (nl["type"] + ":" + nl["slug"]) not in active_refs:
                return nl
        return None
    return newsletters[0]


# Keys whose article_ids are never auto-resolved by resolve_layout_grid_data.
# Dynamic: fetched fresh at request time in build_home_data.
# Manual-only: no fallback exists (editor curation only).
_RESOLVE_SKIP_KEYS = frozenset({
    "lo_ultimo", "lo_mas_leido", "apuntes_del_dia",
    "radio", "newsletter_dia", "recomendadas_lv", "recomendadas_domingo",
    "crucigrama", "edicion_del_dia",
})


def _merge_principal_article_ids(current_ids, edition_ids, edition_all_ids=None):
    """Merge edition_ids into current_ids, preserving editor curation order.

    - Articles in current_ids keep their saved position (editor order preserved).
    - New articles (in edition_ids but absent from current) are inserted at their
      edition index so top_position is respected.
    - If edition_all_ids is provided: articles explicitly in today's edition with
      home_top=False are dropped (admin turned off EN PORTADA). Articles from other
      editions or manually placed (not in edition_all_ids) are always kept.

    Result is capped at BLOCK_ARTICLE_LIMITS["principal"].
    """
    edition_set = set(edition_ids)
    if edition_all_ids:
        # Drop only articles that are in today's edition with home_top=False.
        # Articles from other editions (not in edition_all_ids) are preserved.
        result = [aid for aid in current_ids if aid not in edition_all_ids or aid in edition_set]
    else:
        result = list(current_ids)
    result_set = set(result)
    for edition_idx, article_id in enumerate(edition_ids):
        if article_id not in result_set:
            insert_at = min(edition_idx, len(result))
            result.insert(insert_at, article_id)
            result_set.add(article_id)
    return result[:BLOCK_ARTICLE_LIMITS["principal"]]


def _clear_fallback_blocks(grid_data):
    """Clear article_ids from sections and fallback components so resolve_layout_grid_data
    re-fetches them fresh and the dedup cascade removes articles already in principal.

    Only touches blocks that have an automatic fallback source:
    - sections (all areas — editors curate via source systems, not the layout editor)
    - opinion, le_monde, lento (category-based fallback)

    Never touches: principal (merged separately), suplemento/extra_articles (5am task),
    especial (manual), _RESOLVE_SKIP_KEYS (dynamic or manual-only).
    Active/inactive flags are preserved.
    """
    import copy as _copy
    gd = _copy.deepcopy(grid_data) if isinstance(grid_data, dict) else {}
    for section in gd.get("sections", []):
        section["article_ids"] = []
    # humor excluded: manual editor selection persists across refreshes.
    _FALLBACK_COMP_KEYS = {"opinion", "le_monde", "lento"}
    for comp in gd.get("componentes", []):
        if comp.get("key") in _FALLBACK_COMP_KEYS:
            comp["article_ids"] = []
    return gd


def resolve_layout_grid_data(grid_data, publication=None, layout=None, dedup_populated=False):
    """Return a resolved copy of grid_data where every static block has article_ids populated.

    For blocks with empty article_ids, fallback queries run in deduplication priority order:
      Principal → Suplemento → Especial → Recomendadas → Áreas → opinion / le_monde / lento

    dedup_populated=True also filters already-populated article_ids against higher-priority
    blocks' seen_ids, removing cross-block duplicates from saved data. Use this only when
    persisting (e.g. the pre_save signal) — not for display, so the editor always reflects
    the raw JSON state.

    Blocks in _RESOLVE_SKIP_KEYS are intentionally left as-is:
    - Dynamic (lo_ultimo, lo_mas_leido, apuntes_del_dia): always fetched fresh at request time.
    - Manual-only (recomendadas_*, radio, newsletter_dia): no automatic fallback.
    """
    import copy as _copy
    resolved = _copy.deepcopy(grid_data) if isinstance(grid_data, dict) else get_default_grid_data()
    seen_ids = set()

    # 1. PRINCIPAL — skip fallback and dedup accumulation when inactive
    principal = resolved.setdefault("principal", {"active": True, "article_ids": []})
    if principal.get("active", True):
        p_ids = principal.get("article_ids") or []
        if not p_ids:
            edition = get_current_edition(publication=publication)
            p_ids = [a.id for a in edition.top_articles][:10] if edition else []
            principal["article_ids"] = p_ids
        seen_ids.update(p_ids)

    # 2. SUPLEMENTO — skip fallback and dedup accumulation when inactive
    suplemento = resolved.setdefault("suplemento", {"active": True, "article_ids": []})
    if suplemento.get("active", True):
        s_ids = suplemento.get("article_ids") or []
        if not s_ids:
            source = _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(timezone.localdate().weekday())
            if source:
                articles = _fetch_source_articles(source[0], source[1], limit=7, exclude_ids=seen_ids)
                s_ids = [a.id for a in articles]
                suplemento["article_ids"] = s_ids
        else:
            if dedup_populated:
                # Remove IDs already placed in higher-priority blocks (principal).
                s_ids = [i for i in s_ids if i not in seen_ids]
                suplemento["article_ids"] = s_ids
        seen_ids.update(s_ids)

    # Extra articles (Saturday) — written by resolve_daily_layouts, not auto-computed here
    if layout is not None and getattr(layout, "day", None) == "sa":
        seen_ids.update(resolved.get("extra_articles", {}).get("article_ids", []))

    # 3. ESPECIAL — purely manual; skip dedup accumulation when inactive
    especial = resolved.setdefault("especial", {"active": True, "article_ids": []})
    if especial.get("active", True):
        e_ids = especial.get("article_ids") or []
        if dedup_populated:
            e_ids = [i for i in e_ids if i not in seen_ids]
            especial["article_ids"] = e_ids
        seen_ids.update(e_ids)

    # SUPLEMENTO_EXTRA — purely manual; accumulate active IDs into seen_ids so areas don't repeat
    # them. dedup_populated filters its own article_ids against higher-priority blocks first.
    se_data = resolved.get("suplemento_extra")
    if se_data and se_data.get("active", True):
        se_ids = se_data.get("article_ids") or []
        if dedup_populated:
            se_ids = [i for i in se_ids if i not in seen_ids]
            se_data["article_ids"] = se_ids
        seen_ids.update(se_ids)

    # 4. RECOMENDADAS — purely manual, accumulate before processing Áreas (active only)
    for comp in resolved.get("componentes", []):
        if comp.get("key") in ("recomendadas_lv", "recomendadas_domingo") and comp.get("active", True):
            seen_ids.update(comp.get("article_ids", []))

    # 5. ÁREAS — merge defaults not yet in sections, then resolve fallback with full seen_ids
    # Skip the suplemento source only when suplemento is active. Using article_ids would
    # incorrectly trigger the skip on sibling layouts that inherited propagated IDs but have
    # their suplemento off (e.g. Tuesday after Monday's 5am propagation sets deporte IDs).
    suplemento_has_content = resolved.get("suplemento", {}).get("active", True)
    today_source = (
        _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(timezone.localdate().weekday())
        if suplemento_has_content else None
    )
    existing_slugs = {s.get("slug") for s in resolved.get("sections", [])}
    for da in _DEFAULT_AREAS:
        if da["slug"] not in existing_slugs:
            resolved.setdefault("sections", []).append(
                {"type": da["type"], "slug": da["slug"], "name": da["name"], "active": True, "article_ids": []}
            )
    for area in resolved.get("sections", []):
        if not area.get("active", True):
            continue
        area_type = area.get("type", "section")
        slug = area.get("slug", "")
        if not slug or (today_source and (area_type, slug) == today_source):
            continue
        a_ids = area.get("article_ids") or []
        if not a_ids:
            articles = _fetch_area_articles(area_type, slug, [], exclude_ids=seen_ids)
            a_ids = [a.id for a in articles]
            area["article_ids"] = a_ids
        else:
            if dedup_populated:
                # Remove IDs already placed in higher-priority blocks.
                a_ids = [i for i in a_ids if i not in seen_ids]
                area["article_ids"] = a_ids
        seen_ids.update(a_ids)

    # Merge component definitions not yet present in the saved list (e.g. new components added
    # after the layout was last saved). Appended at the end so the saved order is preserved.
    _existing_comp_keys = {c.get("key") for c in resolved.get("componentes", [])}
    for _defn in COMPONENT_DEFINITIONS:
        if _defn["key"] not in _existing_comp_keys:
            resolved.setdefault("componentes", []).append({"key": _defn["key"], "active": True})

    # 6. OTHER COMPONENTS: opinion, le_monde, lento (skip dynamic and manual-only keys)
    for comp in resolved.get("componentes", []):
        key = comp.get("key", "")
        if key in _RESOLVE_SKIP_KEYS or not comp.get("active", True):
            continue
        c_ids = comp.get("article_ids") or []
        if not c_ids:
            articles = _fetch_component_articles(key, exclude_ids=seen_ids)
            c_ids = [a.id for a in articles]
            comp["article_ids"] = c_ids
        else:
            if dedup_populated:
                # Remove IDs already placed in higher-priority blocks.
                c_ids = [i for i in c_ids if i not in seen_ids]
                comp["article_ids"] = c_ids
        seen_ids.update(c_ids)

    return resolved


def build_home_data(grid_data, publication=None, layout=None):
    """
    Pre-fetch all data needed to render the home template from grid_data.
    Calls resolve_layout_grid_data first so all static blocks have article_ids populated
    with the correct deduplication order. The template reads only from the returned dict.

    Dynamic blocks (lo_ultimo, lo_mas_leido, apuntes_del_dia) are always fetched fresh
    at request time and excluded from the pre-resolved static_ids set.
    """
    result = {
        "principal_active": False,
        "principal_articles": [],
        "suplemento_active": False,
        "suplemento_articles": [],
        "suplemento_title": "",
        "suplemento_slug": "",
        "extra_articles": [],
        "especial_active": False,
        "especial_articles": [],
        "suplemento_extra_active": False,
        "suplemento_extra_articles": [],
        "suplemento_extra_source_type": "",
        "suplemento_extra_source_slug": "",
        "suplemento_extra_title": "",
        "sections": [],
        "componentes": [],
    }

    _tb = time.perf_counter()
    resolved = resolve_layout_grid_data(grid_data, publication=publication, layout=layout)
    logger.warning("  build: resolve=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()

    # --- BULK FETCH ---
    # resolve_layout_grid_data already populated article_ids for every static block.
    # Collect all IDs in one pass and fire a single DB query instead of one per block.
    # lo_ultimo and apuntes_del_dia are excluded: they are always dynamic (no fixed IDs).
    _dynamic_comp_keys = frozenset({"lo_ultimo", "apuntes_del_dia"})

    _bulk_ids: set = set()
    for _block_key in ("principal", "suplemento", "extra_articles", "especial", "suplemento_extra"):
        _bulk_ids.update(resolved.get(_block_key, {}).get("article_ids", []))
    for _area in resolved.get("sections", []):
        if _area.get("active", True):
            _bulk_ids.update(_area.get("article_ids", []))
    for _comp in resolved.get("componentes", []):
        if _comp.get("active", True) and _comp.get("key", "") not in _dynamic_comp_keys:
            _bulk_ids.update(_comp.get("article_ids", []))

    by_id: dict = {}
    if _bulk_ids:
        by_id = {
            a.id: a for a in Article.published.filter(id__in=_bulk_ids)
            .select_related(*_ARTICLE_AUTH_SELECT_RELATED)
            .prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)
        }
    logger.warning("  build: bulk_fetch=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()

    # IDs excluded from "Lo último": principal, suplemento, especial, recomendadas.
    # Areas are intentionally NOT excluded — an article in Deporte can still appear in Lo último.
    # Built directly from resolved IDs (no article objects needed).
    # Only active blocks contribute — inactive blocks don't occupy the pool.
    static_ids: set = set()
    for _block_key in ("principal", "suplemento", "extra_articles", "especial"):
        static_ids.update(resolved.get(_block_key, {}).get("article_ids", []))
    _se_data = resolved.get("suplemento_extra")
    if _se_data and _block_active("suplemento_extra", _se_data.get("active", True)):
        static_ids.update(_se_data.get("article_ids", []))
    for _comp in resolved.get("componentes", []):
        if _comp.get("key") in ("recomendadas_lv", "recomendadas_domingo") and _comp.get("active", True):
            static_ids.update(_comp.get("article_ids", []))

    # PRINCIPAL
    principal_data = resolved.get("principal") or {}
    result["principal_active"] = _block_active("principal", principal_data.get("active", True))
    p_ids = principal_data.get("article_ids", [])
    result["principal_articles"] = [by_id[aid] for aid in p_ids if aid in by_id]
    logger.warning("  build: principal=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()

    # SUPLEMENTO
    _area_name_by_source = {(a["type"], a["slug"]): a["name"] for a in _DEFAULT_AREAS}
    suplemento_data = resolved.get("suplemento", {})
    result["suplemento_active"] = _block_active("suplemento", suplemento_data.get("active", True))
    if result["suplemento_active"]:
        s_ids = suplemento_data.get("article_ids", [])
        result["suplemento_articles"] = [by_id[aid] for aid in s_ids if aid in by_id]
        _today_source = _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(timezone.localdate().weekday())
        if _today_source:
            result["suplemento_title"] = _area_name_by_source.get((_today_source[0], _today_source[1]), "")
            result["suplemento_slug"] = _today_source[1]
        if layout is not None and getattr(layout, "day", None) == "sa":
            extra_ids = resolved.get("extra_articles", {}).get("article_ids", [])
            if extra_ids:
                result["extra_articles"] = [by_id[aid] for aid in extra_ids if aid in by_id]
                result["suplemento_title"] = "Extra"

    # SUPLEMENTO_EXTRA
    se_data = resolved.get("suplemento_extra")
    result["suplemento_extra_active"] = bool(
        se_data and _block_active("suplemento_extra", se_data.get("active", True))
    )
    if result["suplemento_extra_active"]:
        se_ids = se_data.get("article_ids", [])
        result["suplemento_extra_articles"] = [by_id[aid] for aid in se_ids if aid in by_id]
        result["suplemento_extra_source_type"] = se_data.get("source_type", "")
        result["suplemento_extra_source_slug"] = se_data.get("source_slug", "")
        result["suplemento_extra_title"] = _area_name_by_source.get(
            (se_data.get("source_type", ""), se_data.get("source_slug", "")), ""
        )
    logger.warning("  build: suplemento=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()

    # ESPECIAL
    especial_data = resolved.get("especial", {})
    result["especial_active"] = _block_active("especial", especial_data.get("active", True))
    if result["especial_active"]:
        e_ids = especial_data.get("article_ids", [])
        result["especial_articles"] = [by_id[aid] for aid in e_ids if aid in by_id]
    logger.warning("  build: especial=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()

    # ÁREAS Y PUBLICACIONES — always show 12, in the order from resolved (already sorted by
    # recency via _sort_sections_by_recency in tasks.py). Exclude the suplemento source only
    # if suplemento actually has content (not just based on the day of the week).
    _suplemento_has_content = bool(result.get("suplemento_articles"))
    _today_suplemento_source = (
        _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(timezone.localdate().weekday())
        if _suplemento_has_content else None
    )
    _sections_shown = 0
    for area in resolved.get("sections", []):
        if _sections_shown >= 12:
            break
        if not area.get("active", True):
            continue
        area_type = area.get("type", "section")
        slug = area.get("slug", "")
        if not slug or (_today_suplemento_source and (area_type, slug) == _today_suplemento_source):
            continue
        a_ids = area.get("article_ids", [])
        result["sections"].append({
            "type": area_type,
            "slug": slug,
            "name": area.get("name", slug),
            "articles": [by_id[aid] for aid in a_ids if aid in by_id],
            "section_template": _resolve_section_template(slug),
        })
        _sections_shown += 1
    logger.warning("  build: sections=%.1f ms", (time.perf_counter() - _tb) * 1000); _tb = time.perf_counter()

    # COMPONENTES — active ones only
    for item in resolved.get("componentes", []):
        if not item.get("active", True):
            continue
        key = item.get("key", "")
        defn = _COMP_DEF_MAP.get(key, {})
        comp_entry = {
            "key": key,
            "label": defn.get("label", key),
            "description": defn.get("description", ""),
            "sidebar_component_template": _resolve_sidebar_template(key),
            "no_articles": defn.get("no_articles", False),
        }
        if defn.get("newsletter_mode"):
            comp_entry["newsletters"] = _resolve_newsletter_refs(item.get("newsletter_refs", []))
            comp_entry["articles"] = []
        elif key == "lo_mas_leido":
            # Populated hourly by sync_article_views; read from saved article_ids (already in by_id).
            # Fallback to live DB query only when the block has not been populated yet.
            c_ids = item.get("article_ids", [])
            if c_ids:
                comp_entry["articles"] = [by_id[aid] for aid in c_ids if aid in by_id]
            else:
                comp_entry["articles"] = _fetch_component_articles(key)
        elif key == "crucigrama":
            comp_entry["articles"] = []
            crossword_id = item.get("crossword_id")
            if crossword_id:
                # Pre-computed by the Crossword post_save signal — no DB hit needed.
                comp_entry["crossword_id"] = crossword_id
                comp_entry["crossword_image_url"] = item.get("crossword_image_url")
                comp_entry["crossword_url"] = item.get("crossword_url") or "/crucigramas/"
                comp_entry["crossword_date"] = item.get("crossword_date")
            else:
                # Fallback for layouts not yet updated by the signal.
                try:
                    from utopia_cms_ladiaria.models import Crossword
                    cw = Crossword.objects.first()
                    if cw:
                        comp_entry["crossword_id"] = cw.id
                        comp_entry["crossword_image_url"] = cw.image.url if cw.image else None
                        comp_entry["crossword_url"] = "/crucigramas/"
                        comp_entry["crossword_date"] = date_format(
                            cw.date_published, format='l j \\d\\e F', use_l10n=True
                        ).capitalize()
                except ImportError:
                    pass
        elif key in ("lo_ultimo", "apuntes_del_dia"):
            # Dynamic: always fetched fresh at request time — not covered by the bulk fetch.
            if key == "lo_ultimo":
                articles = _fetch_component_articles(
                    key,
                    saved_ids=item.get("article_ids", []),
                    pinned_ids=set(item.get("pinned_ids", [])),
                    exclude_ids=static_ids,
                    soft_pin_saved=True,
                )
            else:
                articles = _fetch_component_articles(key, saved_ids=item.get("article_ids", []), exclude_ids=static_ids)
            if key == "lo_ultimo":
                now = timezone.now()
                for a in articles:
                    minutes = int((now - a.date_published).total_seconds() / 60)
                    a.minutes_ago = minutes if minutes <= 59 else None
            comp_entry["articles"] = articles
        else:
            c_ids = item.get("article_ids", [])
            comp_entry["articles"] = [by_id[aid] for aid in c_ids if aid in by_id]
        result["componentes"].append(comp_entry)

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
    {"type": "category",    "slug": "futuro",     "name": "Futuro"},
]


def _is_before_publishing_time():
    """Return True if the current time is before today's PUBLISHING_TIME.
    Used to gate article visibility in automatic fallback blocks (SUPLEMENTO, ÁREAS)
    so they respect the same 5am cutoff as PRINCIPAL via get_current_edition().
    """
    from core.models import get_publishing_datetime
    return timezone.now() < get_publishing_datetime()


def _fetch_source_articles(source_type, slug, limit, exclude_ids=None):
    """Fetch up to `limit` articles from a publication or category source.
    Shared by SUPLEMENTO and ÁREAS — same fetch logic, different limits.
    Respects PUBLISHING_TIME: before the cutoff, only articles from previous
    editions/days are returned, matching the behavior of get_current_edition().
    When exclude_ids is provided, those article IDs are skipped (deduplication).
    """
    try:
        if source_type == "publication":
            publication = Publication.objects.get(slug=slug)
            edition = get_current_edition(publication=publication)
            if edition:
                articles = list(edition.top_articles)
                if exclude_ids:
                    articles = [a for a in articles if a.id not in exclude_ids]
                return articles[:limit]
        elif source_type == "category":
            category = Category.objects.get(slug=slug)
            qs = category.home.articles_ordered()
            if _is_before_publishing_time():
                qs = qs.filter(date_published__date__lt=timezone.now().date())
            if exclude_ids:
                qs = qs.exclude(id__in=exclude_ids)
            return list(qs[:limit])
    except (Publication.DoesNotExist, Category.DoesNotExist, AttributeError):
        pass
    except Exception as e:
        logger.warning("_fetch_source_articles(%s, %s): %s: %s", source_type, slug, type(e).__name__, e)
    return []


def _fetch_suplemento_articles(suplemento_data, exclude_ids=None):
    """Return SUPLEMENTO articles from saved article_ids.
    Article IDs are written daily by the resolve_daily_layouts Celery task.
    When exclude_ids is provided, those article IDs are skipped (deduplication against Principal).
    """
    saved_ids = suplemento_data.get("article_ids", [])
    if saved_ids:
        if exclude_ids:
            saved_ids = [aid for aid in saved_ids if aid not in exclude_ids]
        by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)}
        return [by_id[aid] for aid in saved_ids if aid in by_id]
    return []


def _fetch_area_articles(area_type, slug, saved_ids, exclude_ids=None):
    """Return articles for an ÁREAS Y PUBLICACIONES block (max 2).
    Priority: saved_ids (manually picked via picker).
    Fallback: 2 articles from the category or publication.
    Special case "local": fetch 1 article from each of colonia/maldonado/paysandu/salto, return the 2 most recent.
    When exclude_ids is provided, fallback queries skip those articles (deduplication).
    """
    if saved_ids:
        by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)}
        return [by_id[aid] for aid in saved_ids if aid in by_id]
    if area_type == "local":
        candidates = []
        for cat_slug in ("colonia", "maldonado", "paysandu", "salto"):
            candidates.extend(_fetch_source_articles("category", cat_slug, limit=1, exclude_ids=exclude_ids))
        candidates.sort(key=lambda a: a.date_published, reverse=True)
        return candidates[:2]
    return _fetch_source_articles(area_type, slug, limit=2, exclude_ids=exclude_ids)


def update_lo_mas_leido_in_layouts():
    """Update the lo_mas_leido article_ids in all HomeLayout objects for the default publication.
    Called by sync_article_views after it writes the updated view counts to ArticleViews,
    so the home reads fresh most-read data without querying the DB on every request.
    """
    from core.views.masleidos import mas_leidos
    try:
        ids = mas_leidos(days=1, limit=5)
    except Exception:
        logger.exception("update_lo_mas_leido_in_layouts: mas_leidos query failed")
        return
    if not ids:
        return
    pub = get_default_publication()
    for layout in HomeLayout.objects.filter(publication=pub):
        grid = layout.grid_data if isinstance(layout.grid_data, dict) else {}
        old_grid = {k: v for k, v in grid.items()}
        updated = False
        for comp in grid.get("componentes", []):
            if comp.get("key") == "lo_mas_leido":
                if comp.get("article_ids") != ids:
                    comp["article_ids"] = list(ids)
                    updated = True
                break
        if updated:
            layout.grid_data = grid
            layout.save(update_fields=["grid_data", "modified"])
            _write_audit_log(layout, old_grid, grid, "sync_article_views")


# Components whose order is always automatic — saved_ids are ignored for these.
_COMPONENTS_AUTO_ORDER = {"lo_mas_leido", "apuntes_del_dia", "radio"}



def _fetch_component_articles(key, saved_ids=None, pinned_ids=None, exclude_ids=None, soft_pin_saved=False):
    """
    Return the article list for a given component key.
    For components not in _COMPONENTS_AUTO_ORDER, saved_ids are used to
    restore the editorial order (same merge logic as PRINCIPAL).
    When exclude_ids is provided, fallback queries skip those articles (deduplication).

    lo_ultimo special behaviour:
      - pinned_ids: articles the editor explicitly fixed. They stay at their saved position
        unless they also appear in exclude_ids (i.e. already placed in a higher-priority block)
        or have been unpublished. In those cases they are evicted and replaced dynamically.
      - soft_pin_saved=True: all saved articles are treated like pinned — they keep their
        position as long as they are published and not excluded. Only evicted slots are filled
        dynamically. Used for regular display so the editor's drag order is respected.
        The "replace unpinned" button calls with soft_pin_saved=False (default) to refresh
        non-pinned slots with the most recently published articles.
      - soft_pin_saved=False (default): only explicitly pinned articles keep their position;
        all other slots are filled with the most recently published available articles.

    Slugs configurable via settings:
      HOMEV4_OPINION_CATEGORY_SLUG   (default: "opinion")
      HOMEV4_APUNTES_SECTION_SLUG    (default: "apuntes-del-dia")
    """
    if key == "lo_ultimo":
        pinned_set = set(pinned_ids or [])
        exclude_set = set(exclude_ids or [])

        if soft_pin_saved and saved_ids:
            # Soft-pin mode: all saved articles keep their position if still valid.
            candidate_ids = [aid for aid in saved_ids if aid not in exclude_set]
            valid_saved = {}
            if candidate_ids:
                valid_saved = {
                    a.id: a
                    for a in Article.published.filter(id__in=candidate_ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)
                }
            anchored = valid_saved
        else:
            # Default mode: only explicitly pinned articles keep their position.
            valid_pinned = {}
            if pinned_set and saved_ids:
                candidate_ids = [aid for aid in saved_ids if aid in pinned_set and aid not in exclude_set]
                if candidate_ids:
                    valid_pinned = {
                        a.id: a
                        for a in Article.published.filter(id__in=candidate_ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)
                    }
            anchored = valid_pinned

        # Dynamic articles fill every slot not covered by an anchored article.
        dynamic_slots = 3 - len(anchored)
        dynamic_articles = []
        if dynamic_slots > 0:
            dynamic_exclude = exclude_set | set(anchored)
            qs = Article.published.select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH).order_by("-date_published")
            qs = qs.exclude(id__in=dynamic_exclude)
            # Exclude articles from specific sources — manual pins still allowed.
            _excl_sections = getattr(
                settings, "HOMEV4_LO_ULTIMO_EXCLUDE_SECTION_SLUGS",
                [getattr(settings, "HOMEV4_HUMOR_SECTION_SLUG", "humor"),
                 getattr(settings, "HOMEV4_APUNTES_SECTION_SLUG", "apuntes-del-dia"),
                 "apuntes-de-la-semana"],
            )
            _excl_categories = getattr(
                settings, "HOMEV4_LO_ULTIMO_EXCLUDE_CATEGORY_SLUGS",
                [getattr(settings, "HOMEV4_OPINION_CATEGORY_SLUG", "opinion"), "libros"],
            )
            _excl_publications = getattr(
                settings, "HOMEV4_LO_ULTIMO_EXCLUDE_PUBLICATION_SLUGS",
                ["lento", "le-monde-diplomatique"],
            )
            if _excl_sections:
                qs = qs.exclude(main_section__section__slug__in=_excl_sections)
            if _excl_categories:
                qs = qs.exclude(main_section__section__category__slug__in=_excl_categories)
            if _excl_publications:
                qs = qs.exclude(main_section__edition__publication__slug__in=_excl_publications)
            dynamic_articles = list(qs[:dynamic_slots])

        if not saved_ids:
            # No saved order yet — return all dynamic articles.
            return dynamic_articles

        # Rebuild in saved order: anchored articles keep their position; every other slot
        # (evicted or not anchored) gets the next dynamic article.
        result = []
        dynamic_iter = iter(dynamic_articles)
        for aid in saved_ids:
            if aid in anchored:
                result.append(anchored[aid])
            else:
                a = next(dynamic_iter, None)
                if a:
                    result.append(a)
        # Append leftover dynamic articles (e.g. saved_ids had fewer than 3 entries).
        for a in dynamic_iter:
            if len(result) >= 3:
                break
            result.append(a)
        return result[:3]

    if key == "lo_mas_leido":
        # days=1 → day__gt=yesterday → effectively today only
        try:
            #TODO: @reidel.rodriguez, revisar mas_ledios porque esta lógica la agregué yo para que se me mostrar los artículos en el template.
            # Antes había;
            # return mas_leidos(days=1, limit=5)

            ids = mas_leidos(days=1, limit=5)
            articles = {a.id: a for a in Article.published.filter(id__in=ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)}
            return [articles[i] for i in ids if i in articles]
        except Exception:
            logger.exception("_fetch_component_articles: lo_mas_leido failed")
            return []

    if key == "opinion":
        if saved_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)}
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
            # section.latest() returns a RawQuerySet that doesn't support select_related/prefetch_related.
            # Re-fetch by ID so the template doesn't trigger N lazy loads for photo and byline.
            raw = list(section.latest(limit=1))
            if raw:
                ids = [a.id for a in raw]
                by_id = {
                    a.id: a for a in Article.published.filter(id__in=ids)
                    .select_related(*_ARTICLE_AUTH_SELECT_RELATED)
                    .prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)
                }
                return [by_id[aid] for aid in ids if aid in by_id]
        except Section.DoesNotExist:
            logger.warning("_fetch_component_articles: apuntes section slug=%r not found", slug)
        return []

    # recomendadas_lv, recomendadas_domingo: fully manual — only saved articles are shown
    if key in ("recomendadas_lv", "recomendadas_domingo"):
        if saved_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)}
            return [by_id[aid] for aid in saved_ids if aid in by_id]
        return []

    if key in ("le_monde", "lento"):
        pub_slug = "le-monde-diplomatique" if key == "le_monde" else "lento"
        if saved_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)}
            return [by_id[aid] for aid in saved_ids if aid in by_id]
        return _fetch_source_articles("publication", pub_slug, limit=2)

    if key == "humor":
        if saved_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=saved_ids).select_related(*_ARTICLE_AUTH_SELECT_RELATED).prefetch_related(*_ARTICLE_PREFETCH_RELATED, *_ARTICLE_EXTRA_PREFETCH)}
            return [by_id[aid] for aid in saved_ids if aid in by_id]
        slug = getattr(settings, "HOMEV4_HUMOR_SECTION_SLUG", "humor")
        try:
            section = Section.objects.get(slug=slug)
            return list(section.latest(limit=1))
        except Section.DoesNotExist:
            logger.warning("_fetch_component_articles: humor section slug=%r not found", slug)
        return []

    # radio, crucigrama: no articles, just a visibility toggle in the layout editor
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

    # Preview mode: staff can open /?preview=1 to see the grid stored in their
    # session by save_preview_session (triggered by the editor "Vista previa" button)
    # or by save_grid (triggered by "Guardar Layout"). The real home is never affected
    # because is_preview requires both the query parameter and staff authentication.
    is_preview = bool(request.GET.get("preview") and request.user.is_staff)
    if is_preview and "preview_grid_data" in request.session:
        grid_data = request.session["preview_grid_data"]
    else:
        grid_data = layout.grid_data if (layout and isinstance(layout.grid_data, dict)) else {}

    # Pre-fetch all content defined by the layout editor into a single dict.
    # The template only reads from home_data — no DB calls inside the template.
    #
    # Performance baseline (2026-03-27, user_auth=True, dev):
    #   Before optimizations: build_home_data ~2066ms, _add_auth_context ~1323ms, render ~1569ms, total ~5256ms
    #   After optimizations:  build_home_data ~320ms,  _add_auth_context ~10ms,   render ~595ms,  total ~963ms
    #
    # Key optimizations applied (commit cf436d7 + 2026-03-27 session):
    #   - _fetch_suplemento_articles, _fetch_area_articles: added select_related(_ARTICLE_AUTH_SELECT_RELATED)
    #     so _add_auth_context does not trigger N+1 lazy loads on main_section→edition→publication per article.
    #   - _fetch_component_articles (lo_ultimo, lo_mas_leido, opinion, recomendadas_*, le_monde, lento):
    #     added select_related as preventive measure for when components are included in _add_auth_context.
    #   - apuntes_del_dia: Section.latest() returns RawQuerySet — re-fetched by ID with select_related +
    #     prefetch_related('photo__extended__photographer', 'byline') to avoid lazy loads in template.
    #   - 2026-05-20: added main_section__section to _ARTICLE_AUTH_SELECT_RELATED and
    #     _ARTICLE_PREFETCH_RELATED for photo/byline to all article queries — eliminating N lazy loads
    #     in the render phase for principal/sections/components. Baseline render: ~500ms [auth], ~800ms [anon].
    _t0 = time.perf_counter()
    home_data = build_home_data(grid_data, publication=publication, layout=layout)
    logger.warning("active_layout build_home_data: %.1f ms", (time.perf_counter() - _t0) * 1000)
    # TODO: review allow_ads logic — wire up is_subscriber once available in context.
    if publication_slug:
        allow_ads = getattr(settings, "HOMEV4_NON_DEFAULT_PUB_ALLOW_ADS", True)
    else:
        allow_ads = True
    papel_url = get_papel_url()
    context = {
        "layout": layout,
        "publication": publication,
        "home_data": home_data,
        "tarde_mode": _is_tarde_mode(layout),
        "is_portada": True,
        "allow_ads": allow_ads,
        "papel_url": papel_url,
        "cache_maxage": _cache_maxage,
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
        # build_home_data already fetches principal_articles with select_related +
        # prefetch_related, so no re-fetch is needed here.
        all_articles = list(home_data.get("principal_articles", []))
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
    # newsletter_dia — resolve which single newsletter to surface to this user.
    #
    # The layout editor stores an ordered list of newsletters for each layout
    # (e.g. "Economía, Justicia" for Monday). The list order is the editorial priority:
    # position 0 is shown first when the user has none of them active.
    #
    # Selection rules (applied in order):
    #   1. Not authenticated or no subscriber profile → show the first newsletter.
    #   2. Authenticated, none active               → show the first newsletter.
    #   3. Authenticated, some active               → show the first one NOT yet active.
    #   4. Authenticated, all active                → show nothing (newsletter_dia_nl = None).
    #
    # The resolved newsletter dict {type, slug, name, periodicity} is placed in
    # context["newsletter_dia_nl"] so the template can render it directly without
    # any further DB access or conditional logic.
    _t_nl = time.perf_counter()
    newsletter_dia_nl = None
    for comp in home_data.get("componentes", []):
        if comp.get("key") == "newsletter_dia":
            newsletters = comp.get("newsletters", [])
            if newsletters:
                newsletter_dia_nl = _pick_newsletter_dia(newsletters, user)
            break
    logger.warning("active_layout newsletter_dia: %.1f ms", (time.perf_counter() - _t_nl) * 1000)
    context["newsletter_dia_nl"] = newsletter_dia_nl

    _t2 = time.perf_counter()
    response = render(request, home_template, context)
    # DEBUG: uncomment to inspect context in the terminal
    #import pprint
    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(context)
    logger.warning("active_layout render: %.1f ms", (time.perf_counter() - _t2) * 1000)

    if is_preview:
        # Inject a fixed banner so the editor knows they are looking at a preview.
        # The message reflects whether the session data came from a save (saved=True)
        # or from an unsaved editor state pushed by the preview button (saved=False).
        # The history.replaceState timestamp makes the URL unique on each load so the
        # service worker cannot serve a stale cached version on the next refresh.
        # NOTE: refresh still has issues when the SW intercepts before Django — pending fix.
        saved = request.session.get("preview_grid_saved", False)
        msg = "Vista previa · contenido guardado ✓" if saved else "Vista previa · cambios sin guardar"
        banner = (
            '<div style="position:fixed;top:0;left:0;right:0;z-index:99999;'
            'background:#417690;color:#fff;padding:8px 16px;'
            'font-family:sans-serif;font-size:13px;text-align:center;">'
            + msg + '</div>'
            '<script>history.replaceState(null,"","/?preview=1&_t="+Date.now());</script>'
        )
        content = response.content.decode("utf-8")
        response.content = content.replace("</body>", banner + "</body>", 1).encode("utf-8")

    return response


def _fetch_source_articles_post_5am(source_type, slug, limit, exclude_ids=None):
    """Like _fetch_source_articles but always uses today's content, ignoring PUBLISHING_TIME.
    Used by the Preview 5am editor to show what will be available after the gate opens.
    When exclude_ids is provided, those article IDs are skipped (deduplication).
    """
    from core.models import Edition
    today = timezone.localdate()
    try:
        if source_type == "publication":
            publication = Publication.objects.get(slug=slug)
            edition = Edition.objects.filter(publication=publication, date_published=today).order_by("-date_published").first()
            if edition:
                articles = list(edition.top_articles)
                if exclude_ids:
                    articles = [a for a in articles if a.id not in exclude_ids]
                return articles[:limit]
        elif source_type == "category":
            category = Category.objects.get(slug=slug)
            qs = category.home.articles_ordered().filter(date_published__date=today)
            if exclude_ids:
                qs = qs.exclude(id__in=exclude_ids)
            return list(qs[:limit])
    except Exception as e:
        logger.warning("_fetch_source_articles_post_5am(%s, %s): %s", source_type, slug, e)
    return []


def _fetch_extra_article_ids_for_preview(today):
    """Fetch extra article IDs from FSNewsletter for the given date.
    Returns [] if the model is unavailable or no FSNewsletter exists for today.
    Isolated into its own function so tests can patch homev4.views._fetch_extra_article_ids_for_preview
    directly instead of having to intercept builtins.__import__.
    """
    try:
        FSNewsletter = __import__(
            "utopia_cms_ladiaria.models", fromlist=["FSNewsletter"]
        ).FSNewsletter
        fs_nl = FSNewsletter.objects.get(day=today)
        return [a.id for a in fs_nl.extra_articles.order_by("fs_newsletter_extra_articles")]
    except Exception:
        return []


def _resolve_today_grid_data(publication):
    """Return a grid_data dict pre-filled with today's article IDs for principal and suplemento,
    bypassing the PUBLISHING_TIME gate. Used by the Preview 5am editor.

    Base structure (which blocks are active/inactive, sections, componentes) comes from
    the layout that will actually be active at the next 5am — the same layout the Celery
    task will write to. This way Pablo sees exactly which blocks are on/off without having
    to guess, and the editor automatically adapts if the schedule changes.

    "Next 5am" logic:
      - 00:00–04:59 → 5am of today   (Pablo is working on the upcoming morning)
      - 05:00–23:59 → 5am of tomorrow (today's 5am already passed)
    """
    import datetime as _dt
    from core.models import Edition
    today = timezone.localdate()
    now_time = timezone.localtime().time()

    publishing_hour, publishing_minute = [int(x) for x in settings.PUBLISHING_TIME.split(":")]
    publishing_time = _dt.time(publishing_hour, publishing_minute)

    # Determine the weekday for the NEXT 5am so get_active_layout simulates the
    # moment the Celery task runs, not the moment Pablo opens the editor.
    if now_time < publishing_time:
        # Still before 5am — next publishing is today's 5am.
        target_weekday = today.weekday()
    else:
        # Already past 5am — next publishing is tomorrow's 5am.
        target_weekday = (today.weekday() + 1) % 7

    base_layout = HomeLayout.get_active_layout(publication, at_time=publishing_time, at_weekday=target_weekday)
    grid = dict(base_layout.grid_data) if base_layout and isinstance(base_layout.grid_data, dict) else get_default_grid_data()

    # On weekends (Saturday=5, Sunday=6) the home shows the "Fin de semana" edition
    # (publication slug "findesemana"), not "la diaria". There is no "ladiaria" edition
    # on weekends, so filtering by publication=ladiaria would return None every time.
    # The "Fin de semana" edition is created once per weekend with date_published=Saturday
    # and kept unchanged through Sunday — so we fetch the most recent one without
    # filtering by today's date (a date=Sunday filter would miss the Saturday edition).
    # On weekdays we filter by date_published=today to get exactly today's edition;
    # no 5am gate is applied here because this function is only called from the
    # Preview 5am editor, which is explicitly designed to bypass that gate.
    weekday = today.weekday()
    if weekday >= 5:
        fds_pub = Publication.objects.filter(slug="findesemana").first()
        edition = Edition.objects.filter(publication=fds_pub).order_by("-date_published").first() if fds_pub else None
    else:
        edition = Edition.objects.filter(publication=publication, date_published=today).order_by("-date_published").first()
    principal_ids = [a.id for a in edition.top_articles] if edition else []
    principal_block = dict(grid.get("principal") or {})
    principal_block["article_ids"] = principal_ids
    grid["principal"] = principal_block

    source = _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(today.weekday())
    seen_ids = set(principal_ids)
    suplemento_ids = [a.id for a in _fetch_source_articles_post_5am(source[0], source[1], limit=7, exclude_ids=seen_ids)] if source else []
    suplemento_block = dict(grid.get("suplemento") or {})
    suplemento_block["article_ids"] = suplemento_ids
    grid["suplemento"] = suplemento_block

    # On Saturdays populate extra_articles from FSNewsletter so the Preview 5am editor
    # shows Pablo the correct content before he saves the pending grid.
    if today.weekday() == 5:
        extra_ids = _fetch_extra_article_ids_for_preview(today)
        if extra_ids:
            extra_block = dict(grid.get("extra_articles") or {})
            extra_block["article_ids"] = extra_ids
            grid["extra_articles"] = extra_block

    return grid


def build_editor_data(grid_data, publication=None):
    """Build the editor context dict from grid_data.
    Calls resolve_layout_grid_data so all static blocks have article_ids populated with
    the correct deduplication order — same logic used by build_home_data.
    Used by both the admin change_view and the Preview 5am view.
    """
    resolved = resolve_layout_grid_data(grid_data, publication=publication)

    principal_data = resolved.get("principal") or {}
    suplemento_data = resolved.get("suplemento", {})
    especial_data = resolved.get("especial", {})

    result = {
        "principal_active": principal_data.get("active", True),
        "principal_articles": [],
        # True when grid_data had no saved article_ids for principal (editor sees fallback state)
        "principal_is_fallback": not bool((grid_data or {}).get("principal", {}).get("article_ids")),
        "suplemento_active": suplemento_data.get("active", True),
        "suplemento_articles": [],
        "especial_active": especial_data.get("active", True),
        "especial_articles": [],
        "sections": [],
        "componentes": [],
    }

    # PRINCIPAL
    p_ids = principal_data.get("article_ids", [])
    if p_ids:
        by_id = {a.id: a for a in Article.published.filter(id__in=p_ids)}
        result["principal_articles"] = [by_id[aid] for aid in p_ids if aid in by_id]

    # SUPLEMENTO
    s_ids = suplemento_data.get("article_ids", [])
    if s_ids:
        by_id = {a.id: a for a in Article.published.filter(id__in=s_ids)}
        result["suplemento_articles"] = [by_id[aid] for aid in s_ids if aid in by_id]

    # ESPECIAL
    e_ids = especial_data.get("article_ids", [])
    if e_ids:
        by_id = {a.id: a for a in Article.published.filter(id__in=e_ids)}
        result["especial_articles"] = [by_id[aid] for aid in e_ids if aid in by_id]

    # SUPLEMENTO_EXTRA — optional block; None when absent (no block rendered)
    se_data = resolved.get("suplemento_extra")
    result["suplemento_extra"] = se_data
    result["suplemento_extra_articles"] = []
    if se_data:
        se_ids = se_data.get("article_ids", [])
        if se_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=se_ids)}
            result["suplemento_extra_articles"] = [by_id[aid] for aid in se_ids if aid in by_id]

    # ÁREAS — resolved dict already has all default areas merged and article_ids populated
    for area in resolved.get("sections", []):
        area_type = area.get("type", "section")
        slug = area.get("slug", "")
        if not slug:
            continue
        a_ids = area.get("article_ids", [])
        sec_info = {
            "type": area_type,
            "slug": slug,
            "name": area.get("name", slug),
            "active": area.get("active", True),
            "preview_articles": [],
        }
        if a_ids:
            by_id = {a.id: a for a in Article.published.filter(id__in=a_ids)}
            sec_info["preview_articles"] = [by_id[aid] for aid in a_ids if aid in by_id]
        result["sections"].append(sec_info)

    # IDs already placed in principal/suplemento/especial/suplemento_extra — exclude from lo_ultimo
    # preview, mirroring the same deduplication that build_home_data applies at request time.
    editor_static_ids = (
        {a.id for a in result["principal_articles"]}
        | {a.id for a in result["suplemento_articles"]}
        | {a.id for a in result["especial_articles"]}
        | {a.id for a in result["suplemento_extra_articles"]}
    )

    # COMPONENTES — all defined components in order; dynamic blocks fetch fresh since
    # resolve_layout_grid_data intentionally leaves their article_ids empty
    saved_comps_raw = resolved.get("componentes", [])
    if isinstance(saved_comps_raw, list):
        seen_keys = set()
        for item in saved_comps_raw:
            key = item.get("key", "")
            defn = _COMP_DEF_MAP.get(key)
            if not defn or key in seen_keys:
                continue
            seen_keys.add(key)
            comp_dict = {
                "key": key,
                "label": defn["label"],
                "description": defn["description"],
                "active": item.get("active", True),
                "has_picker": defn.get("has_picker", False),
                "replace_mode": defn.get("replace_mode", False),
                "pin_mode": defn.get("pin_mode", False),
                "newsletter_mode": defn.get("newsletter_mode", False),
                "sortable_articles": defn.get("sortable_articles", True),
                "max_articles": BLOCK_ARTICLE_LIMITS.get(key),
            }
            if defn.get("newsletter_mode"):
                comp_dict["newsletters"] = _resolve_newsletter_refs(item.get("newsletter_refs", []))
                comp_dict["articles"] = []
            elif key == "lo_ultimo":
                # Always fetched fresh so the editor reflects the live resolved state.
                pinned_ids = set(item.get("pinned_ids", []))
                comp_dict["pinned_ids"] = list(pinned_ids)
                comp_dict["articles"] = _fetch_component_articles(
                    key,
                    saved_ids=item.get("article_ids", []),
                    pinned_ids=pinned_ids,
                    exclude_ids=editor_static_ids,
                    soft_pin_saved=True,
                )
            else:
                c_ids = item.get("article_ids", [])
                if c_ids:
                    by_id = {a.id: a for a in Article.published.filter(id__in=c_ids)}
                    comp_dict["articles"] = [by_id[aid] for aid in c_ids if aid in by_id]
                else:
                    comp_dict["articles"] = _fetch_component_articles(key)
            result["componentes"].append(comp_dict)
        for defn in COMPONENT_DEFINITIONS:
            if defn["key"] not in seen_keys:
                comp_dict = {
                    "key": defn["key"],
                    "label": defn["label"],
                    "description": defn["description"],
                    "active": True,
                    "has_picker": defn.get("has_picker", False),
                    "replace_mode": defn.get("replace_mode", False),
                    "pin_mode": defn.get("pin_mode", False),
                    "newsletter_mode": defn.get("newsletter_mode", False),
                    "sortable_articles": defn.get("sortable_articles", True),
                    "max_articles": BLOCK_ARTICLE_LIMITS.get(defn["key"]),
                }
                if defn.get("newsletter_mode"):
                    comp_dict["newsletters"] = []
                    comp_dict["articles"] = []
                elif defn["key"] == "lo_ultimo":
                    comp_dict["pinned_ids"] = []
                    comp_dict["articles"] = _fetch_component_articles(
                        defn["key"], pinned_ids=set(), exclude_ids=editor_static_ids, soft_pin_saved=True,
                    )
                else:
                    comp_dict["articles"] = _fetch_component_articles(defn["key"])
                result["componentes"].append(comp_dict)
    else:
        for defn in COMPONENT_DEFINITIONS:
            saved = saved_comps_raw.get(defn["key"], {})
            comp_dict = {
                "key": defn["key"],
                "label": defn["label"],
                "description": defn["description"],
                "active": saved.get("active", True),
                "has_picker": defn.get("has_picker", False),
                "pin_mode": defn.get("pin_mode", False),
                "newsletter_mode": defn.get("newsletter_mode", False),
                "sortable_articles": defn.get("sortable_articles", True),
            }
            if defn.get("newsletter_mode"):
                comp_dict["newsletters"] = _resolve_newsletter_refs(saved.get("newsletter_refs", []))
                comp_dict["articles"] = []
            elif defn["key"] == "lo_ultimo":
                pinned_ids = set(saved.get("pinned_ids", []))
                comp_dict["pinned_ids"] = list(pinned_ids)
                comp_dict["articles"] = _fetch_component_articles(
                    defn["key"],
                    saved_ids=saved.get("article_ids", []),
                    pinned_ids=pinned_ids,
                    exclude_ids=editor_static_ids,
                    soft_pin_saved=True,
                )
            else:
                comp_dict["articles"] = _fetch_component_articles(defn["key"])
            result["componentes"].append(comp_dict)

    return result


def _static_hash(path):
    """Return a short hash of the static file content for cache busting."""
    import hashlib
    from django.contrib.staticfiles import finders
    full_path = finders.find(path)
    if not full_path:
        return "0"
    try:
        with open(full_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    except OSError:
        return "0"


@never_cache
@staff_member_required
def preview_5am(request):
    """Editor view for preparing tomorrow's home before 5am.
    Shows today's articles (bypassing the PUBLISHING_TIME gate) so editors can
    curate the layout in advance. Saves to pending_grid_data instead of grid_data,
    so the live home is not affected until the Celery task moves it at 5am.
    """
    publication = get_default_publication()
    today = timezone.localdate()

    pending_layout = HomeLayout.objects.filter(
        publication=publication,
        pending_grid_data__isnull=False,
    ).first()

    if pending_layout and isinstance(pending_layout.pending_grid_data, dict):
        pending = pending_layout.pending_grid_data
        if pending.get("date") == today.isoformat():
            grid_data = pending["grid"]
        else:
            grid_data = _resolve_today_grid_data(publication)
    else:
        grid_data = _resolve_today_grid_data(publication)

    editor_data = build_editor_data(grid_data, publication=publication)
    has_pending = pending_layout is not None and isinstance(pending_layout.pending_grid_data, dict) and pending_layout.pending_grid_data.get("date") == today.isoformat()

    any_layout = HomeLayout.objects.filter(publication=publication).first()
    # Compute target_weekday (next publishing day) to pass the correct suplemento source
    # slug to the editor JS for dimming — same logic used by the 5am Celery task.
    _publishing_h, _publishing_m = [int(x) for x in settings.PUBLISHING_TIME.split(":")]
    _now_time = timezone.localtime().time()
    _target_weekday = today.weekday() if _now_time < datetime.time(_publishing_h, _publishing_m) else (today.weekday() + 1) % 7
    _target_source = _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(_target_weekday)
    context = {
        "editor_data": editor_data,
        "save_grid_url": "/homev4/save-pending/",
        "article_search_url": f"/homev4/article-search/?layout_id={any_layout.pk}" if any_layout else "/homev4/article-search/",
        "newsletter_search_url": "/homev4/newsletter-search/",
        "blocks_config": LAYOUT_BLOCKS_CONFIG,
        "layout_editor_js_version": _static_hash("homev4/layout_editor.js"),
        "layout_editor_css_version": _static_hash("homev4/layout_editor.css"),
        "is_preview_5am": True,
        "has_pending": has_pending,
        "today_suplemento_source_slug": _target_source[1] if _target_source else "",
    }
    return render(request, "homev4/preview_5am.html", context)


@never_cache
@staff_member_required
def preview_5am_render(request):
    """Render the home template using pending_grid_data (Preview 5am content) without modifying any layout."""
    publication = get_default_publication()
    today = timezone.localdate()

    pending_layout = HomeLayout.objects.filter(
        publication=publication,
        pending_grid_data__isnull=False,
    ).first()

    grid_data = None
    if pending_layout and isinstance(pending_layout.pending_grid_data, dict):
        pending = pending_layout.pending_grid_data
        if pending.get("date") == today.isoformat():
            grid_data = pending["grid"]

    if grid_data is None:
        grid_data = _resolve_today_grid_data(publication)

    any_layout = HomeLayout.objects.filter(publication=publication).first()
    home_data = build_home_data(grid_data, publication=publication, layout=any_layout)
    home_template = getattr(settings, "HOMEV4_HOME_TEMPLATE", _HOME_TEMPLATE)
    papel_url = get_papel_url()
    return render(request, home_template, {
        "layout": any_layout,
        "publication": publication,
        "home_data": home_data,
        "newsletter_dia_nl": None,
        "tarde_mode": False,
        "is_portada": True,
        "allow_ads": False,
        "papel_url": papel_url,
    })


@staff_member_required
def reset_pending_grid(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    publication = get_default_publication()
    HomeLayout.objects.filter(publication=publication).update(pending_grid_data=None)
    return JsonResponse({"status": "ok"})


@never_cache
@staff_member_required
def save_preview_session(request):
    """Store the current editor grid_data in the session for preview rendering.

    Called by the layout editor "Vista previa" button (layout_editor.js) before
    opening /?preview=1 in a new tab. active_layout reads preview_grid_data from
    the session when is_preview=True so the tab shows the unsaved editor state.

    The session key preview_grid_saved controls the banner message:
      True  → "contenido guardado ✓"   (set here when saved=True, and by save_grid)
      False → "cambios sin guardar"    (set here when saved=False)
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        request.session["preview_grid_data"] = data.get("grid_data", {})
        request.session["preview_grid_saved"] = bool(data.get("saved", False))
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@never_cache
def nl_dia_status(request, publication_slug=None):
    """Return the newsletter_dia to surface to the current user as JSON.

    Called by the home page JS to hydrate the newsletter_dia sidebar component
    after the page is served from cache.  Returns {"nl": null} when no newsletter
    needs to be shown (user subscribed to all, or unauthenticated).
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"nl": None})

    if publication_slug:
        publication = get_object_or_404(Publication, slug=publication_slug)
    else:
        publication = get_default_publication()

    layout = HomeLayout.get_active_layout(publication)
    grid_data = layout.grid_data if (layout and isinstance(layout.grid_data, dict)) else {}

    newsletters = []
    for comp in grid_data.get("componentes", []):
        if comp.get("key") == "newsletter_dia":
            newsletters = _resolve_newsletter_refs(comp.get("newsletter_refs", []))
            break

    if not newsletters:
        return JsonResponse({"nl": None})

    newsletter_dia_nl = _pick_newsletter_dia(newsletters, user)

    if newsletter_dia_nl is None:
        return JsonResponse({"nl": None})

    nltype = "c" if newsletter_dia_nl["type"] == "category" else "p"
    preview_url_name = "c-nl-browser-authpreview" if nltype == "c" else "p-nl-browser-authpreview"
    result = {
        **newsletter_dia_nl,
        "nltype": nltype,
        "subscribe_url": reverse("nl-auth-subscribe", kwargs={"nltype": nltype, "nlslug": newsletter_dia_nl["slug"]}),
        "preview_url": reverse(preview_url_name, kwargs={"slug": newsletter_dia_nl["slug"]}),
    }
    return JsonResponse({"nl": result})


@staff_member_required
@never_cache
def save_pending_grid(request):
    """Save grid_data to pending_grid_data on the first layout of the default publication.
    Called by the Preview 5am editor. Does not propagate — the Celery task does that at 5am.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    publication = get_default_publication()
    try:
        data = json.loads(request.body)
        grid_data = data.get("grid_data", {})
        layout = HomeLayout.objects.filter(publication=publication).first()
        if not layout:
            return JsonResponse({"error": "No layout found"}, status=404)
        layout.pending_grid_data = {"date": timezone.localdate().isoformat(), "grid": grid_data}
        layout.save(update_fields=["pending_grid_data"])
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
