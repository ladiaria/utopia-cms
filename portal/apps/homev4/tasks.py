import logging

from django.db import transaction
from django.utils import timezone

from celeryapp import celery_app

from .models import HomeLayout
from .views import _fetch_source_articles, _SUPLEMENTO_SOURCE_BY_WEEKDAY, _propagate_article_ids

logger = logging.getLogger("homev4")


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
    publications = list(
        HomeLayout.objects.values_list("publication", flat=True).distinct()
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
                with transaction.atomic():
                    pending_layout.pending_grid_data = None
                    pending_layout.save(update_fields=["pending_grid_data"])
                    layout.grid_data = grid_to_apply
                    layout.save()
                    layout.refresh_from_db(fields=["grid_data"])
                    _propagate_article_ids(layout, layout.grid_data)
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

        gd = layout.grid_data if isinstance(layout.grid_data, dict) else {}

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

        logger.info(
            "resolve_daily_layouts_task: publication=%s layout=%d — suplemento=%d ids, extra=%d ids",
            publication.slug,
            layout.pk,
            len(suplemento_ids),
            len(extra_ids),
        )
