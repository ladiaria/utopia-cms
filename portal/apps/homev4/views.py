import json
import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from core.models import Article, Publication, Section, Category, get_current_edition
from core.views.masleidos import mas_leidos
from thedaily.utils import unsubscribed_newsletters

from .models import HomeLayout

logger = logging.getLogger("homev4")


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

_COMP_DEF_MAP = {d["key"]: d for d in COMPONENT_DEFINITIONS}

DEFAULT_COMPONENTES = [{"key": d["key"], "active": True} for d in COMPONENT_DEFINITIONS]


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

    edition = get_current_edition(publication=publication)

    # PRINCIPAL
    principal_data = grid_data.get("principal") or {}
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

    return result


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
        slug = getattr(settings, "HOMEV4_OPINION_CATEGORY_SLUG", "opinion")
        try:
            category = Category.objects.get(slug=slug)
            if hasattr(category, "home"):
                db_articles = list(category.home.articles_ordered()[:2])
                return _merge_article_order(db_articles, saved_ids)
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

    # radio: no articles, just a visibility toggle in the layout editor
    # recomendadas_lv, recomendadas_domingo, newsletter_dia: pending implementation
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
    home_data = build_home_data(grid_data, publication=publication)

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
        all_articles = list(home_data.get("principal_articles", []))
        for sec in home_data.get("sections", []):
            all_articles.extend(sec.get("articles", []))

        # Populate restricteds / restricteds_allowed / follows in context.
        _add_auth_context(context, user, all_articles)

        # Unsubscribed newsletters banner: show only if the feature is enabled,
        # the user has a subscriber profile with an email, and hasn't closed it yet.
        if (
            getattr(settings, "HOMEV3_NEWSLETTERS_HEADER_ENABLED", False)
            and hasattr(user, "subscriber")
            and user.email
            and not request.session.get("unsubscribed_nls_notice_closed")
        ):
            context["unsubscribed_newsletters"] = unsubscribed_newsletters(user.subscriber)

    return render(request, "homev4/home.html", context)
