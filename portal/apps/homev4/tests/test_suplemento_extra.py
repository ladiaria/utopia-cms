"""
Unit tests for the suplemento_extra block feature.

suplemento_extra is a single optional block in grid_data that behaves like ESPECIAL:
  - Fully manual: article_ids set by the editor, never auto-filled by Celery tasks.
  - Persists until explicitly removed or disabled — no saved_date expiry.
  - Propagates to all sibling layouts via _propagate_article_ids.
  - Source (source_type + source_slug) chosen by the editor from the 4 suplemento
    sources: deporte (publication), mundo (category), economia (publication),
    cultura (category).

Data structure in grid_data:
  {
    "suplemento_extra": {
      "active": True,
      "source_type": "publication",   # or "category"
      "source_slug": "deporte",
      "article_ids": [101, 102, 103],
    }
  }

When suplemento_extra is absent from grid_data the feature is not in use — no error,
no phantom block.

Test groups:
  1. resolve_layout_grid_data — dedup: suplemento_extra contributes to seen_ids
  2. resolve_layout_grid_data — dedup: principal dedup applies to suplemento_extra
  3. resolve_layout_grid_data — manual: block is never auto-filled
  4. build_home_data — suplemento_extra articles excluded from lo_ultimo
  5. _propagate_article_ids — full block propagated to siblings (create, update, delete)
"""
import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from homev4.views import build_home_data, resolve_layout_grid_data

# Fixed date: Monday so suplemento fallback is active — lets us confirm suplemento_extra
# dedup is independent of whether suplemento itself has content.
_MONDAY = datetime.date(2026, 4, 20)
_SUNDAY = datetime.date(2026, 4, 19)


def _art(article_id):
    a = MagicMock()
    a.id = article_id
    return a


def _make_excludable_fetcher(available_ids):
    """Fetch function that honours exclude_ids, simulating a DB query."""
    def fetch(*args, exclude_ids=None, **kwargs):
        return [_art(i) for i in available_ids if i not in (exclude_ids or set())]
    return fetch


def _suplemento_extra(article_ids, *, source_type="publication", source_slug="deporte", active=True):
    """Helper to build a suplemento_extra grid block."""
    return {
        "active": active,
        "source_type": source_type,
        "source_slug": source_slug,
        "article_ids": list(article_ids),
    }


# ---------------------------------------------------------------------------
# Group 1 & 2 & 3 — resolve_layout_grid_data
# ---------------------------------------------------------------------------

class SupplementoExtraResolveTest(SimpleTestCase):
    """
    Deduplication and manual-only behaviour of suplemento_extra inside
    resolve_layout_grid_data.
    """

    def _run(self, grid_data, *, principal_ids=(1, 2), suplemento_ids=(3, 4),
             area_ids=(5, 6), date=_MONDAY, dedup_populated=False):
        """Run resolve_layout_grid_data with mocked DB calls."""
        with patch("homev4.views.get_current_edition") as mock_edition, \
             patch("homev4.views._fetch_source_articles",
                   side_effect=_make_excludable_fetcher(suplemento_ids)), \
             patch("homev4.views._fetch_area_articles",
                   side_effect=lambda area_type, slug, saved_ids, exclude_ids=None: (
                       [_art(i) for i in saved_ids] if saved_ids
                       else [_art(i) for i in area_ids if i not in (exclude_ids or set())]
                   )), \
             patch("homev4.views._fetch_component_articles", return_value=[]), \
             patch("homev4.views.timezone") as mock_tz:
            mock_edition.return_value.top_articles = [_art(i) for i in principal_ids]
            mock_tz.localdate.return_value = date
            mock_tz.now.return_value = MagicMock()
            return resolve_layout_grid_data(grid_data, dedup_populated=dedup_populated)

    # --- Group 1: suplemento_extra contributes to seen_ids ---

    def test_suplemento_extra_excludes_from_area_fallback(self):
        """Article in active suplemento_extra must NOT appear in area fallback."""
        # area_ids pool includes 99, which is also in suplemento_extra
        grid = {"suplemento_extra": _suplemento_extra([99])}
        result = self._run(grid, principal_ids=(1,), suplemento_ids=(3,), area_ids=(99, 5))
        area_ids_in_result = [
            aid for sec in result.get("sections", []) for aid in sec.get("article_ids", [])
        ]
        self.assertNotIn(99, area_ids_in_result)
        self.assertIn(5, area_ids_in_result)

    def test_inactive_suplemento_extra_not_in_seen_ids(self):
        """Inactive suplemento_extra must NOT add its articles to seen_ids."""
        # article 99 is in an inactive suplemento_extra — it should be available to areas
        grid = {"suplemento_extra": _suplemento_extra([99], active=False)}
        result = self._run(grid, principal_ids=(1,), suplemento_ids=(3,), area_ids=(99, 5))
        area_ids_in_result = [
            aid for sec in result.get("sections", []) for aid in sec.get("article_ids", [])
        ]
        self.assertIn(99, area_ids_in_result)

    def test_suplemento_extra_independent_of_suplemento(self):
        """suplemento and suplemento_extra each contribute their own articles to seen_ids."""
        grid = {
            "suplemento":       {"active": True, "article_ids": [10, 11]},
            "suplemento_extra": _suplemento_extra([20, 21]),
        }
        # Both 11 (suplemento) and 20 (suplemento_extra) are in area pool — both must be excluded
        result = self._run(grid, principal_ids=(1,), suplemento_ids=(), area_ids=(11, 20, 5))
        area_ids_in_result = [
            aid for sec in result.get("sections", []) for aid in sec.get("article_ids", [])
        ]
        self.assertNotIn(11, area_ids_in_result)
        self.assertNotIn(20, area_ids_in_result)
        self.assertIn(5, area_ids_in_result)

    def test_absent_suplemento_extra_causes_no_error(self):
        """Grid without suplemento_extra key resolves without error."""
        result = self._run({})
        self.assertIn("principal", result)
        self.assertNotIn("suplemento_extra", result)

    # --- Group 2: principal dedup applies to suplemento_extra ---

    def test_principal_in_suplemento_extra_removed_with_dedup_populated(self):
        """dedup_populated=True: article already in principal is removed from suplemento_extra."""
        grid = {
            "suplemento_extra": _suplemento_extra([2, 99]),  # 2 is also in principal
        }
        result = self._run(grid, principal_ids=(1, 2), suplemento_ids=(), dedup_populated=True)
        self.assertNotIn(2, result["suplemento_extra"]["article_ids"])
        self.assertIn(99, result["suplemento_extra"]["article_ids"])

    def test_suplemento_extra_preserved_without_dedup_populated(self):
        """Without dedup_populated, overlap with principal is kept as-is."""
        grid = {
            "suplemento_extra": _suplemento_extra([2, 99]),  # 2 overlaps principal
        }
        result = self._run(grid, principal_ids=(1, 2), suplemento_ids=(), dedup_populated=False)
        self.assertIn(2, result["suplemento_extra"]["article_ids"])
        self.assertIn(99, result["suplemento_extra"]["article_ids"])

    # --- Group 3: suplemento_extra is never auto-filled ---

    def test_empty_suplemento_extra_not_auto_filled(self):
        """resolve_layout_grid_data never auto-fills suplemento_extra — it is always manual."""
        grid = {"suplemento_extra": _suplemento_extra([])}
        result = self._run(grid, principal_ids=(1,), suplemento_ids=(3,), area_ids=(5,))
        self.assertEqual(result["suplemento_extra"]["article_ids"], [])

    def test_suplemento_extra_source_fields_preserved(self):
        """resolve_layout_grid_data must not clear source_type or source_slug."""
        grid = {"suplemento_extra": _suplemento_extra([10], source_type="category", source_slug="cultura")}
        result = self._run(grid)
        self.assertEqual(result["suplemento_extra"]["source_type"], "category")
        self.assertEqual(result["suplemento_extra"]["source_slug"], "cultura")


# ---------------------------------------------------------------------------
# Group 4 — build_home_data: suplemento_extra articles in static_ids
# ---------------------------------------------------------------------------

class SupplementoExtraBuildHomeDataTest(SimpleTestCase):
    """
    suplemento_extra articles must be included in static_ids so they are
    excluded from lo_ultimo (same rule as suplemento and especial).
    """

    def _article_filter_mock(self):
        def side_effect(*args, **kwargs):
            ids = list(kwargs.get("id__in", []))
            articles = [_art(i) for i in ids]
            qs = MagicMock()
            qs.__iter__ = lambda self: iter(articles)
            qs.select_related.return_value = qs
            return qs
        published = MagicMock()
        published.filter.side_effect = side_effect
        return published

    def _get_lo_ultimo_exclude_ids(self, resolved_grid):
        captured = {}

        def mock_fetch(key, saved_ids=None, pinned_ids=None, exclude_ids=None, **kwargs):
            captured[key] = frozenset(exclude_ids or [])
            return []

        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved_grid), \
             patch("homev4.views.Article") as mock_art, \
             patch("homev4.views._fetch_component_articles", side_effect=mock_fetch), \
             patch("homev4.views._block_active", side_effect=lambda _key, val: bool(val)), \
             patch("homev4.views._SUPLEMENTO_SOURCE_BY_WEEKDAY", {}), \
             patch("homev4.views.timezone") as mock_tz:
            mock_art.published = self._article_filter_mock()
            mock_tz.localdate.return_value = _SUNDAY
            mock_tz.now.return_value = MagicMock()
            build_home_data(resolved_grid, publication=None, layout=None)

        return captured.get("lo_ultimo", frozenset())

    def test_suplemento_extra_excluded_from_lo_ultimo(self):
        """Articles in active suplemento_extra must be in lo_ultimo's exclude_ids."""
        resolved = {
            "principal":       {"active": True, "article_ids": [1]},
            "suplemento":      {"active": True, "article_ids": []},
            "suplemento_extra": _suplemento_extra([50, 51]),
            "especial":        {"active": True, "article_ids": []},
            "sections": [],
            "componentes": [{"key": "lo_ultimo", "active": True, "article_ids": []}],
        }
        exclude_ids = self._get_lo_ultimo_exclude_ids(resolved)
        self.assertIn(50, exclude_ids)
        self.assertIn(51, exclude_ids)

    def test_inactive_suplemento_extra_not_excluded_from_lo_ultimo(self):
        """Articles in inactive suplemento_extra must NOT be in lo_ultimo's exclude_ids."""
        resolved = {
            "principal":       {"active": True, "article_ids": [1]},
            "suplemento":      {"active": True, "article_ids": []},
            "suplemento_extra": _suplemento_extra([50, 51], active=False),
            "especial":        {"active": True, "article_ids": []},
            "sections": [],
            "componentes": [{"key": "lo_ultimo", "active": True, "article_ids": []}],
        }
        exclude_ids = self._get_lo_ultimo_exclude_ids(resolved)
        self.assertNotIn(50, exclude_ids)
        self.assertNotIn(51, exclude_ids)


# ---------------------------------------------------------------------------
# Group 5 — _propagate_article_ids: full block propagation
# ---------------------------------------------------------------------------

class SupplementoExtraPropagateTest(SimpleTestCase):
    """
    _propagate_article_ids must handle suplemento_extra as a full block:
      - Create it in siblings that don't have it yet (including source_type, source_slug, active).
      - Update article_ids in siblings that already have it, preserving their active flag.
      - Remove it from siblings when source has no suplemento_extra (delete propagation).
    """

    def _run_propagate(self, source_grid, sibling_grid_data):
        from homev4.views import _propagate_article_ids

        source_layout = MagicMock()
        source_layout.pk = 1

        sibling = MagicMock()
        sibling.pk = 2
        sibling.grid_data = sibling_grid_data

        with patch("homev4.views.HomeLayout") as mock_hl, \
             patch("homev4.views.timezone"), \
             patch("homev4.views._write_audit_log"):
            mock_hl.objects.select_for_update.return_value \
                .exclude.return_value.filter.return_value = [sibling]
            _propagate_article_ids(source_layout, source_grid)

        return sibling.grid_data

    def test_propagate_creates_full_block_in_sibling_without_it(self):
        """When sibling has no suplemento_extra, the full block is created from source."""
        result = self._run_propagate(
            source_grid={"suplemento_extra": _suplemento_extra(
                [10, 20], source_type="category", source_slug="cultura"
            )},
            sibling_grid_data={},
        )
        self.assertIn("suplemento_extra", result)
        self.assertEqual(result["suplemento_extra"]["article_ids"], [10, 20])
        self.assertEqual(result["suplemento_extra"]["source_type"], "category")
        self.assertEqual(result["suplemento_extra"]["source_slug"], "cultura")
        self.assertTrue(result["suplemento_extra"]["active"])

    def test_propagate_syncs_active_flag_from_source(self):
        """active propagates from source so enabling/disabling in one layout syncs all siblings."""
        result = self._run_propagate(
            source_grid={"suplemento_extra": _suplemento_extra([10, 20], active=True)},
            sibling_grid_data={"suplemento_extra": _suplemento_extra([], active=False)},
        )
        self.assertEqual(result["suplemento_extra"]["article_ids"], [10, 20])
        # Source had active=True — sibling's active=False must be overwritten.
        self.assertTrue(result["suplemento_extra"]["active"])

    def test_propagate_syncs_deactivation_to_siblings(self):
        """Deactivating in the source layout propagates active=False to all siblings."""
        result = self._run_propagate(
            source_grid={"suplemento_extra": _suplemento_extra([10, 20], active=False)},
            sibling_grid_data={"suplemento_extra": _suplemento_extra([10, 20], active=True)},
        )
        self.assertFalse(result["suplemento_extra"]["active"])

    def test_propagate_preserves_sibling_source_fields(self):
        """Propagation must not overwrite sibling's source_type and source_slug."""
        result = self._run_propagate(
            source_grid={"suplemento_extra": _suplemento_extra(
                [10], source_type="publication", source_slug="deporte"
            )},
            sibling_grid_data={"suplemento_extra": _suplemento_extra(
                [], source_type="category", source_slug="cultura"
            )},
        )
        # Source fields in siblings are their own — only article_ids propagates
        self.assertEqual(result["suplemento_extra"]["source_type"], "category")
        self.assertEqual(result["suplemento_extra"]["source_slug"], "cultura")

    def test_propagate_removes_suplemento_extra_from_sibling_when_source_has_none(self):
        """
        If source has no suplemento_extra, siblings must lose it too.
        This implements the 'si borran ese bloque, todos los layouts lo borran' rule.
        """
        result = self._run_propagate(
            source_grid={},  # no suplemento_extra in source
            sibling_grid_data={"suplemento_extra": _suplemento_extra([10, 20])},
        )
        self.assertNotIn("suplemento_extra", result)
