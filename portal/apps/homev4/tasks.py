import copy
import logging

from kombu.exceptions import OperationalError

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from celeryapp import celery_app

from .models import HomeLayout
from .views import _fetch_source_articles, _SUPLEMENTO_SOURCE_BY_WEEKDAY, _propagate_article_ids, _write_audit_log

logger = logging.getLogger("homev4")

inspector = celery_app.control.inspect()

try:
    _refresh_workers = [
        w for w, queues in (inspector.active_queues() or {}).items()
        if any(q["name"] == settings.CELERY_TASK_ROUTES["refresh-home-layouts"]["queue"] for q in queues)
    ]
except (AttributeError, KeyError, OperationalError):
    _refresh_workers = []


def _resolve_suplemento_ids():
    """Fetch article IDs for today's suplemento source. Returns empty list if no source for today."""
    source = _SUPLEMENTO_SOURCE_BY_WEEKDAY.get(timezone.localdate().weekday())
    if not source:
        return []
    articles = _fetch_source_articles(source[0], source[1], limit=7)
    return [a.id for a in articles]


def _resolve_extra_article_ids():
    """Fetch extra article IDs from FSNewsletter for today (Saturday only). Returns empty list on failure."""
    try:
        FSNewsletter = __import__(
            "utopia_cms_ladiaria.models", fromlist=["FSNewsletter"]
        ).FSNewsletter
        fs_nl = FSNewsletter.objects.get(day=timezone.localdate())
        return [a.id for a in fs_nl.extra_articles.order_by("fs_newsletter_extra_articles")]
    except Exception:
        logger.debug("_resolve_extra_article_ids: FSNewsletter not available or not found for today")
        return []


@celery_app.task(name="resolve-daily-layouts")
def resolve_daily_layouts_task():
    """
    Runs daily at 5am. For each publication with active layouts, resolves automatic
    content (suplemento, extra_articles) and writes the article IDs into the active
    layout's grid_data, then propagates to all sibling layouts via _propagate_article_ids.
    This ensures build_home_data() has a single source of truth — the layout itself.
    """
    suplemento_ids = _resolve_suplemento_ids()
    is_saturday = timezone.localdate().weekday() == 5
    extra_ids = _resolve_extra_article_ids() if is_saturday else []

    today = timezone.localdate()
    # order_by() clears the model's default ordering so distinct() deduplicates
    # by publication alone — without it MySQL includes day/start_time in the
    # SELECT DISTINCT and returns one row per layout instead of one per publication.
    publications = list(
        HomeLayout.objects.order_by().values_list("publication", flat=True).distinct()
    )
    if not publications:
        logger.info("resolve_daily_layouts_task: no publications with layouts found")
        return

    from core.models import Publication
    for pub_id in publications:
        try:
            publication = Publication.objects.get(pk=pub_id)
        except Publication.DoesNotExist:
            continue

        # Check if an editor prepared content in advance via the Preview 5am editor.
        pending_layout = HomeLayout.objects.filter(
            publication=publication,
            pending_grid_data__isnull=False,
        ).first()

        if pending_layout and isinstance(pending_layout.pending_grid_data, dict):
            pending = pending_layout.pending_grid_data
            if pending.get("date") == today.isoformat():
                grid_to_apply = pending["grid"]
                layout = HomeLayout.get_active_layout(publication) or pending_layout
                # Capture before overwriting so audit log can diff what changed.
                old_grid = layout.grid_data if isinstance(layout.grid_data, dict) else {}
                with transaction.atomic():
                    pending_layout.pending_grid_data = None
                    pending_layout.save(update_fields=["pending_grid_data"])
                    layout.grid_data = grid_to_apply
                    layout.save()
                    layout.refresh_from_db(fields=["grid_data"])
                    _propagate_article_ids(layout, layout.grid_data)
                    _write_audit_log(layout, old_grid, layout.grid_data, "celery:5am")
                logger.info(
                    "resolve_daily_layouts_task: publication=%s — applied pending_grid_data from editor",
                    publication.slug,
                )
                continue
            else:
                # Stale pending from a previous day — discard it.
                pending_layout.pending_grid_data = None
                pending_layout.save(update_fields=["pending_grid_data"])
                logger.info(
                    "resolve_daily_layouts_task: publication=%s — discarded stale pending_grid_data (date=%s)",
                    publication.slug,
                    pending.get("date"),
                )

        layout = HomeLayout.get_active_layout(publication)
        if not layout:
            logger.debug("resolve_daily_layouts_task: no active layout for publication=%s", publication.slug)
            continue

        # Deep copy so mutations to gd's nested dicts do not corrupt old_grid,
        # which is used as the "before" state in _write_audit_log.
        old_grid = copy.deepcopy(layout.grid_data) if isinstance(layout.grid_data, dict) else {}
        gd = dict(layout.grid_data) if isinstance(layout.grid_data, dict) else {}

        suplemento_block = gd.get("suplemento") if isinstance(gd.get("suplemento"), dict) else {}
        suplemento_block["article_ids"] = suplemento_ids
        gd["suplemento"] = suplemento_block

        if is_saturday:
            extra_block = gd.get("extra_articles") if isinstance(gd.get("extra_articles"), dict) else {}
            extra_block["article_ids"] = extra_ids
            gd["extra_articles"] = extra_block

        with transaction.atomic():
            layout.grid_data = gd
            layout.save()
            layout.refresh_from_db(fields=["grid_data"])
            _propagate_article_ids(layout, layout.grid_data)
            _write_audit_log(layout, old_grid, layout.grid_data, "celery:5am")

        logger.info(
            "resolve_daily_layouts_task: publication=%s layout=%d — suplemento=%d ids, extra=%d ids",
            publication.slug,
            layout.pk,
            len(suplemento_ids),
            len(extra_ids),
        )


def _sort_sections_by_recency(grid_data):
    """Sort grid_data["sections"] in-place by the date_published of each section's
    first article, most recent first. Sections without articles keep their current position.
    Uses a single query for all first-article IDs to avoid N+1.
    """
    import datetime
    from core.models import Article

    sections = grid_data.get("sections", [])
    first_ids = [s["article_ids"][0] for s in sections if s.get("article_ids")]
    if not first_ids:
        return

    dates = dict(
        Article.objects.filter(pk__in=first_ids).values_list("id", "date_published")
    )
    min_date = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    sections.sort(
        key=lambda s: dates.get(s["article_ids"][0], min_date) if s.get("article_ids") else min_date,
        reverse=True,
    )


@celery_app.task(name="refresh-home-layouts")
def refresh_home_layouts_task():
    """
    Triggered on article save. For each active layout:
    1. Merges new edition top_articles into principal (preserving editor's saved order).
    2. Clears sections and fallback component article_ids.
    3. Re-resolves via resolve_layout_grid_data so the dedup cascade removes from
       sections any article already in principal, and fills sections fresh from source.
    Suplemento, especial, extra_articles, and _RESOLVE_SKIP_KEYS are never touched.
    """
    from .views import resolve_layout_grid_data, _merge_principal_article_ids, _clear_fallback_blocks
    from core.models import Publication, get_current_edition

    publications = list(HomeLayout.objects.order_by().values_list("publication", flat=True).distinct())
    if not publications:
        return

    for pub_id in publications:
        try:
            publication = Publication.objects.get(pk=pub_id)
        except Publication.DoesNotExist:
            continue

        layout = HomeLayout.get_active_layout(publication)
        if not layout:
            continue

        old_grid = copy.deepcopy(layout.grid_data) if isinstance(layout.grid_data, dict) else {}

        # Step 1: merge new edition articles into principal at their top_position index.
        # On weekends (Saturday=5, Sunday=6) the relevant edition is "Fin de semana"
        # (publication slug "findesemana"), not "la diaria". Without this branch,
        # get_current_edition(ladiaria) returns Friday's edition and its articles would
        # be injected into the weekend home every time a journalist saves an article —
        # silently overwriting whatever Pablo prepared for the weekend.
        # get_current_edition applies the 5am gate (date_published <= today after 5am),
        # so on Sunday it correctly picks up Saturday's "Fin de semana" edition because
        # date_published=Saturday satisfies date_published <= Sunday.
        weekday = timezone.localdate().weekday()
        if weekday >= 5:
            fds_pub = Publication.objects.filter(slug="findesemana").first()
            edition = get_current_edition(publication=fds_pub) if fds_pub else None
        else:
            edition = get_current_edition(publication=publication)
        edition_ids = [a.id for a in edition.top_articles] if edition else []
        current_principal = old_grid.get("principal", {})
        current_principal_ids = current_principal.get("article_ids", []) if isinstance(current_principal, dict) else []
        merged_ids = _merge_principal_article_ids(current_principal_ids, edition_ids)

        gd = copy.deepcopy(old_grid)
        if not isinstance(gd.get("principal"), dict):
            gd["principal"] = {"active": True}
        gd["principal"]["article_ids"] = merged_ids

        # Step 2: clear sections and fallback components so resolve re-fetches them.
        gd = _clear_fallback_blocks(gd)

        # Step 3: re-resolve — fills cleared blocks with dedup against updated principal.
        resolved = resolve_layout_grid_data(gd, publication=publication, layout=layout)

        # Step 4: sort sections by the date_published of their first article (most recent first).
        # Pre-computing the order here so the FE receives sections already sorted — zero
        # sorting cost at request time.
        _sort_sections_by_recency(resolved)

        with transaction.atomic():
            layout.grid_data = resolved
            layout.save()
            layout.refresh_from_db(fields=["grid_data"])
            _propagate_article_ids(layout, resolved)
            _write_audit_log(layout, old_grid, resolved, "celery:refresh")

        logger.info("refresh_home_layouts_task: publication=%s layout=%d refreshed", publication.slug, layout.pk)


def refresh_home_layouts():
    """Enqueue refresh-home-layouts task unless one is already active or scheduled."""
    task_name = refresh_home_layouts_task.name
    found = False

    if _refresh_workers:
        try:
            active = inspector.active() or {}
        except (TimeoutError, BrokenPipeError):
            active = {}
        for w in _refresh_workers:
            if any(t.get("name") == task_name for t in active.get(w, [])):
                found = True
                break

    if not found and _refresh_workers:
        try:
            scheduled = inspector.scheduled() or {}
        except (TimeoutError, BrokenPipeError):
            scheduled = {}
        for w in _refresh_workers:
            if any(t.get("name") == task_name for t in scheduled.get(w, [])):
                found = True
                break

    if not found:
        try:
            refresh_home_layouts_task.delay()
        except OperationalError as e:
            logger.error("refresh_home_layouts_task could not be started: %s", e)
    else:
        logger.debug("Task '%s' is already active or scheduled, no action taken.", task_name)
