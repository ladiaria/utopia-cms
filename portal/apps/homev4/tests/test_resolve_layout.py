"""
Unit tests for resolve_layout_grid_data, build_home_data, and the pre_save signal.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.

resolve_layout_grid_data deduplication priority (the "golden rule"):
  Principal → Suplemento → Especial → Recomendadas → Áreas → opinion/le_monde/lento

The golden rule applies to BOTH empty blocks (fallback fetch) and saved article_ids:
  an ID already in a higher-priority block is removed from any lower-priority block,
  regardless of whether those IDs were saved manually or filled by fallback.

build_home_data Lo último exclusion rule:
  Excluded: principal, suplemento, especial, recomendadas.
  NOT excluded: area blocks — an article in Deporte can still appear in Lo último.

pre_save signal (_deduplicate_grid_data):
  Runs resolve_layout_grid_data before every HomeLayout.save() that touches grid_data,
  guaranteeing a single consistent deduplication point for all write paths.
"""
import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from homev4.apps import _deduplicate_grid_data
from homev4.tasks import _sort_sections_by_recency
from homev4.views import build_home_data, resolve_layout_grid_data


# A known Monday: weekday()=0 → _SUPLEMENTO_SOURCE_BY_WEEKDAY maps to ("publication", "deporte")
_MONDAY = datetime.date(2026, 4, 20)

# A known Sunday: weekday()=6 → no suplemento source (key not in dict)
_SUNDAY = datetime.date(2026, 4, 19)


def _art(article_id):
    """Minimal mock Article with only an id attribute."""
    a = MagicMock()
    a.id = article_id
    return a


def _make_excludable_fetcher(available_ids):
    """Return a fetch function that simulates DB exclusion from exclude_ids."""
    def fetch(*args, exclude_ids=None, **kwargs):
        pool = [_art(i) for i in available_ids]
        return [a for a in pool if a.id not in (exclude_ids or set())]
    return fetch


class ResolveLayoutGridDataTest(SimpleTestCase):
    """
    Each test patches only the DB-touching functions, leaving the deduplication
    logic in resolve_layout_grid_data fully exercised.
    """

    def _run(self, grid_data, *, principal_ids=(1, 2), suplemento_ids=(3, 4),
             area_ids=(5, 6), date=_MONDAY, dedup_populated=False):
        """
        Run resolve_layout_grid_data with predictable mocks.
        fetch_area and fetch_source respect exclude_ids to simulate DB behaviour.
        fetch_component returns empty for everything (not relevant to dedup tests).
        dedup_populated mirrors the parameter added to resolve_layout_grid_data.
        """
        with patch("homev4.views.get_current_edition") as mock_edition, \
             patch("homev4.views._fetch_source_articles",
                   side_effect=_make_excludable_fetcher(suplemento_ids)), \
             patch("homev4.views._fetch_area_articles",
                   side_effect=lambda area_type, slug, saved_ids, exclude_ids=None:
                   (
                       [_art(i) for i in saved_ids] if saved_ids
                       else [a for a in [_art(i) for i in area_ids]
                             if a.id not in (exclude_ids or set())]
                   )), \
             patch("homev4.views._fetch_component_articles", return_value=[]), \
             patch("homev4.views.timezone") as mock_tz:
            mock_edition.return_value.top_articles = [_art(i) for i in principal_ids]
            mock_tz.localdate.return_value = date
            mock_tz.now.return_value = MagicMock()
            return resolve_layout_grid_data(grid_data, dedup_populated=dedup_populated)

    # -----------------------------------------------------------------------
    # Fallback population
    # -----------------------------------------------------------------------

    def test_empty_grid_populates_principal(self):
        """Empty grid_data: principal gets article_ids from edition.top_articles."""
        result = self._run({})
        self.assertEqual(result["principal"]["article_ids"], [1, 2])

    def test_empty_grid_populates_suplemento_on_monday(self):
        """On Monday (weekday=0) suplemento should be resolved from its source."""
        result = self._run({}, suplemento_ids=(3, 4))
        self.assertEqual(result["suplemento"]["article_ids"], [3, 4])

    def test_no_suplemento_on_sunday(self):
        """Sunday has no entry in _SUPLEMENTO_SOURCE_BY_WEEKDAY → suplemento stays empty."""
        result = self._run({}, date=_SUNDAY)
        self.assertEqual(result["suplemento"]["article_ids"], [])

    def test_default_areas_added_to_sections(self):
        """Default areas missing from grid_data are appended with resolved article_ids."""
        result = self._run({})
        slugs = {s["slug"] for s in result["sections"]}
        # Spot-check a few known default areas
        self.assertIn("mundo", slugs)
        self.assertIn("cultura", slugs)
        self.assertIn("local", slugs)

    # -----------------------------------------------------------------------
    # Saved IDs are preserved (no fallback when already curated)
    # -----------------------------------------------------------------------

    def test_saved_principal_ids_preserved(self):
        """principal with saved_ids: fallback is not called, IDs kept as-is."""
        grid = {"principal": {"active": True, "article_ids": [99, 98]}}
        # edition returns [1,2] but should NOT be used
        result = self._run(grid, principal_ids=(1, 2))
        self.assertEqual(result["principal"]["article_ids"], [99, 98])

    def test_saved_suplemento_ids_preserved_when_no_conflict(self):
        """suplemento with saved_ids that don't overlap principal: IDs kept as-is."""
        grid = {"suplemento": {"active": True, "article_ids": [77, 78]}}
        # principal_ids=(1,2) — no overlap with [77,78]
        result = self._run(grid)
        self.assertEqual(result["suplemento"]["article_ids"], [77, 78])

    def test_saved_area_ids_preserved_when_no_conflict(self):
        """Area with saved_ids that don't overlap higher-priority blocks: IDs kept as-is."""
        grid = {
            "sections": [
                {"type": "category", "slug": "mundo", "name": "Mundo",
                 "active": True, "article_ids": [55, 56]},
            ]
        }
        # principal_ids=(1,2), suplemento_ids=(3,4) — no overlap with [55,56]
        result = self._run(grid)
        mundo = next(s for s in result["sections"] if s["slug"] == "mundo")
        self.assertEqual(mundo["article_ids"], [55, 56])

    # -----------------------------------------------------------------------
    # Deduplication: golden rule
    # -----------------------------------------------------------------------

    def test_principal_excludes_from_suplemento(self):
        """Article in principal must NOT appear in suplemento fallback."""
        # principal=[1,2], suplemento pool=[1,3] → suplemento gets only [3]
        result = self._run({}, principal_ids=(1, 2), suplemento_ids=(1, 3))
        self.assertNotIn(1, result["suplemento"]["article_ids"])
        self.assertNotIn(2, result["suplemento"]["article_ids"])
        self.assertIn(3, result["suplemento"]["article_ids"])

    def test_principal_excludes_from_areas(self):
        """Article in principal must NOT appear in any area fallback."""
        result = self._run({}, principal_ids=(1, 2), area_ids=(1, 5))
        all_area_ids = set()
        for section in result["sections"]:
            all_area_ids.update(section["article_ids"])
        self.assertNotIn(1, all_area_ids)
        self.assertNotIn(2, all_area_ids)
        self.assertIn(5, all_area_ids)

    def test_suplemento_excludes_from_areas(self):
        """Article in suplemento must NOT appear in any area fallback."""
        # principal=[1], suplemento pool=[3] → seen_ids={1,3} when areas are fetched
        result = self._run({}, principal_ids=(1,), suplemento_ids=(3,), area_ids=(3, 5))
        all_area_ids = set()
        for section in result["sections"]:
            all_area_ids.update(section["article_ids"])
        self.assertNotIn(3, all_area_ids)
        self.assertIn(5, all_area_ids)

    def test_especial_excludes_from_areas(self):
        """Article in especial must NOT appear in any area fallback."""
        grid = {"especial": {"active": True, "article_ids": [10]}}
        result = self._run(grid, principal_ids=(), suplemento_ids=(), area_ids=(10, 5))
        all_area_ids = set()
        for section in result["sections"]:
            all_area_ids.update(section["article_ids"])
        self.assertNotIn(10, all_area_ids)
        self.assertIn(5, all_area_ids)

    def test_recomendadas_excludes_from_areas(self):
        """
        Article in recomendadas must NOT appear in any area fallback.
        This was the pre-fix gap: Áreas was processed before Recomendadas
        entered seen_ids, allowing duplicates.
        """
        grid = {
            "componentes": [
                {"key": "recomendadas_lv", "active": True, "article_ids": [20]},
            ]
        }
        result = self._run(grid, principal_ids=(), suplemento_ids=(), area_ids=(20, 5))
        all_area_ids = set()
        for section in result["sections"]:
            all_area_ids.update(section["article_ids"])
        self.assertNotIn(20, all_area_ids)
        self.assertIn(5, all_area_ids)

    def test_recomendadas_domingo_excludes_from_areas(self):
        """Same as above but with recomendadas_domingo."""
        grid = {
            "componentes": [
                {"key": "recomendadas_domingo", "active": True, "article_ids": [21]},
            ]
        }
        result = self._run(grid, principal_ids=(), suplemento_ids=(), area_ids=(21, 6))
        all_area_ids = set()
        for section in result["sections"]:
            all_area_ids.update(section["article_ids"])
        self.assertNotIn(21, all_area_ids)

    def test_no_cross_block_duplicates_with_overlapping_pool(self):
        """
        No article ID may appear in more than one block when all pools overlap.
        Stress-tests the full deduplication chain.
        """
        # All pools share article 1 — it should only end up in principal
        result = self._run(
            {},
            principal_ids=(1, 2),
            suplemento_ids=(1, 2, 3),
            area_ids=(1, 2, 3, 4, 5),
        )
        all_ids = []
        all_ids.extend(result["principal"]["article_ids"])
        all_ids.extend(result["suplemento"]["article_ids"])
        all_ids.extend(result.get("especial", {}).get("article_ids", []))
        for section in result["sections"]:
            all_ids.extend(section["article_ids"])
        # No duplicate IDs across blocks
        self.assertEqual(len(all_ids), len(set(all_ids)),
                         f"Duplicate IDs found across blocks: {all_ids}")

    def test_inactive_area_not_included(self):
        """Inactive areas must be skipped entirely."""
        grid = {
            "sections": [
                {"type": "category", "slug": "mundo", "name": "Mundo",
                 "active": False, "article_ids": []},
            ]
        }
        result = self._run(grid)
        mundo = next((s for s in result["sections"] if s["slug"] == "mundo"), None)
        # The inactive section is in the list but resolve should have skipped fetching for it
        # (it's present in resolved since deepcopy preserves it, but not fetched/processed)
        if mundo:
            self.assertEqual(mundo["article_ids"], [])

    # -----------------------------------------------------------------------
    # Deduplication of saved (non-empty) article_ids — requires dedup_populated=True
    # -----------------------------------------------------------------------

    def test_saved_suplemento_overlap_preserved_without_dedup_populated(self):
        """Without dedup_populated, saved suplemento IDs that overlap principal are kept as-is."""
        grid = {
            "principal":  {"active": True, "article_ids": [1, 2]},
            "suplemento": {"active": True, "article_ids": [2, 3]},
        }
        result = self._run(grid)
        # 2 overlaps principal but must NOT be removed — editor shows raw JSON
        self.assertIn(2, result["suplemento"]["article_ids"])

    def test_saved_area_overlap_preserved_without_dedup_populated(self):
        """Without dedup_populated, saved area IDs that overlap principal are kept as-is."""
        grid = {
            "principal": {"active": True, "article_ids": [1, 2]},
            "sections": [
                {"type": "category", "slug": "mundo", "name": "Mundo",
                 "active": True, "article_ids": [2, 55]},
            ],
        }
        result = self._run(grid)
        mundo = next(s for s in result["sections"] if s["slug"] == "mundo")
        self.assertIn(2, mundo["article_ids"])

    def test_principal_in_saved_suplemento_is_removed(self):
        """dedup_populated=True: a principal ID saved in suplemento must be removed."""
        grid = {
            "principal":  {"active": True, "article_ids": [1, 2]},
            "suplemento": {"active": True, "article_ids": [2, 3]},  # 2 overlaps principal
        }
        result = self._run(grid, dedup_populated=True)
        self.assertNotIn(2, result["suplemento"]["article_ids"])
        self.assertIn(3, result["suplemento"]["article_ids"])
        self.assertEqual(result["principal"]["article_ids"], [1, 2])

    def test_principal_in_saved_area_is_removed(self):
        """dedup_populated=True: a principal ID saved in an area must be removed."""
        grid = {
            "principal": {"active": True, "article_ids": [1, 2]},
            "sections": [
                {"type": "category", "slug": "mundo", "name": "Mundo",
                 "active": True, "article_ids": [2, 55]},  # 2 overlaps principal
            ],
        }
        result = self._run(grid, dedup_populated=True)
        mundo = next(s for s in result["sections"] if s["slug"] == "mundo")
        self.assertNotIn(2, mundo["article_ids"])
        self.assertIn(55, mundo["article_ids"])

    def test_principal_in_saved_especial_is_removed(self):
        """dedup_populated=True: a principal ID saved in especial must be removed."""
        grid = {
            "principal": {"active": True, "article_ids": [1, 2]},
            "especial":  {"active": True, "article_ids": [2, 10]},  # 2 overlaps principal
        }
        result = self._run(grid, dedup_populated=True)
        self.assertNotIn(2, result["especial"]["article_ids"])
        self.assertIn(10, result["especial"]["article_ids"])

    def test_no_cross_block_duplicates_with_saved_overlap(self):
        """
        dedup_populated=True stress test: when saved IDs in suplemento and areas overlap
        with principal, no article ID appears in more than one block after resolve.
        """
        grid = {
            "principal":  {"active": True, "article_ids": [1, 2]},
            "suplemento": {"active": True, "article_ids": [2, 3]},  # 2 overlaps
            "sections": [
                {"type": "category", "slug": "mundo", "name": "Mundo",
                 "active": True, "article_ids": [3, 55]},  # 3 overlaps suplemento
            ],
        }
        result = self._run(grid, dedup_populated=True)
        all_ids = []
        all_ids.extend(result["principal"]["article_ids"])
        all_ids.extend(result["suplemento"]["article_ids"])
        all_ids.extend(result.get("especial", {}).get("article_ids", []))
        for section in result["sections"]:
            all_ids.extend(section["article_ids"])
        self.assertEqual(len(all_ids), len(set(all_ids)),
                         f"Duplicate IDs found across blocks: {all_ids}")

    def test_dedup_populated_filters_saved_dynamic_component_ids(self):
        """dedup_populated=True: saved IDs in a dynamic component (opinion) that overlap
        principal are removed — same rule as suplemento and areas."""
        grid = {
            "principal": {"active": True, "article_ids": [1, 2]},
            "componentes": [
                {"key": "opinion", "active": True, "article_ids": [2, 50]},  # 2 overlaps
            ],
        }
        result = self._run(grid, dedup_populated=True)
        opinion = next((c for c in result["componentes"] if c["key"] == "opinion"), None)
        self.assertIsNotNone(opinion)
        self.assertNotIn(2, opinion["article_ids"])
        self.assertIn(50, opinion["article_ids"])

    def test_resolve_skip_keys_not_filtered_even_with_dedup_populated(self):
        """dedup_populated=True must NOT filter lo_ultimo saved IDs — it is in _RESOLVE_SKIP_KEYS
        and its curated content is the editorial source of truth."""
        grid = {
            "principal": {"active": True, "article_ids": [1, 2]},
            "componentes": [
                {"key": "lo_ultimo", "active": True, "article_ids": [2, 50]},  # 2 overlaps principal
            ],
        }
        result = self._run(grid, dedup_populated=True)
        lo = next((c for c in result["componentes"] if c["key"] == "lo_ultimo"), None)
        self.assertIsNotNone(lo)
        # lo_ultimo is in _RESOLVE_SKIP_KEYS — must be left untouched
        self.assertIn(2, lo["article_ids"])
        self.assertIn(50, lo["article_ids"])

    def test_inactive_recomendadas_not_added_to_seen_ids(self):
        """
        Inactive recomendadas component must NOT contribute to seen_ids —
        its articles should still be available for areas.
        """
        grid = {
            "componentes": [
                {"key": "recomendadas_lv", "active": False, "article_ids": [30]},
            ]
        }
        result = self._run(grid, principal_ids=(), suplemento_ids=(), area_ids=(30, 5))
        all_area_ids = set()
        for section in result["sections"]:
            all_area_ids.update(section["article_ids"])
        # Inactive recomendadas should NOT exclude article 30 from areas
        self.assertIn(30, all_area_ids)


class BuildHomeDataLoUltimoTest(SimpleTestCase):
    """
    Tests the exclusion rule for "Lo último" in build_home_data.

    Rule: Lo último only excludes articles from principal, suplemento, especial,
    and recomendadas. Area blocks are intentionally NOT excluded so that a recently
    published article that landed in an area can still appear in Lo último.

    Strategy: mock resolve_layout_grid_data to return a known grid, mock
    Article.published to echo back articles for requested IDs, and capture
    the exclude_ids passed to _fetch_component_articles for the "lo_ultimo" key.
    """

    def _article_filter_mock(self):
        """Mock for Article.published that returns _art() objects for requested IDs."""
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
        """
        Run build_home_data with a pre-resolved grid and return the frozenset of
        exclude_ids that were passed to _fetch_component_articles for 'lo_ultimo'.
        """
        captured = {}

        def mock_fetch(key, saved_ids=None, exclude_ids=None):
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

    def test_area_articles_not_excluded_from_lo_ultimo(self):
        """An article in an area block must NOT be excluded from Lo último."""
        resolved = {
            "principal":  {"active": True, "article_ids": [1, 2]},
            "suplemento": {"active": True, "article_ids": [3]},
            "especial":   {"active": True, "article_ids": []},
            "sections": [
                {"type": "category", "slug": "mundo", "name": "Mundo",
                 "active": True, "article_ids": [5, 6]},
            ],
            "componentes": [
                {"key": "lo_ultimo", "active": True, "article_ids": []},
            ],
        }
        exclude = self._get_lo_ultimo_exclude_ids(resolved)
        self.assertNotIn(5, exclude, "Area article 5 must not be excluded from Lo último")
        self.assertNotIn(6, exclude, "Area article 6 must not be excluded from Lo último")

    def test_principal_excluded_from_lo_ultimo(self):
        """Articles in principal must be excluded from Lo último."""
        resolved = {
            "principal":  {"active": True, "article_ids": [1, 2]},
            "suplemento": {"active": True, "article_ids": []},
            "sections": [],
            "componentes": [{"key": "lo_ultimo", "active": True, "article_ids": []}],
        }
        exclude = self._get_lo_ultimo_exclude_ids(resolved)
        self.assertIn(1, exclude)
        self.assertIn(2, exclude)

    def test_suplemento_excluded_from_lo_ultimo(self):
        """Articles in suplemento must be excluded from Lo último."""
        resolved = {
            "principal":  {"active": True, "article_ids": []},
            "suplemento": {"active": True, "article_ids": [10, 11]},
            "sections": [],
            "componentes": [{"key": "lo_ultimo", "active": True, "article_ids": []}],
        }
        exclude = self._get_lo_ultimo_exclude_ids(resolved)
        self.assertIn(10, exclude)
        self.assertIn(11, exclude)

    def test_especial_excluded_from_lo_ultimo(self):
        """Articles in especial must be excluded from Lo último."""
        resolved = {
            "principal":  {"active": True, "article_ids": []},
            "suplemento": {"active": True, "article_ids": []},
            "especial":   {"active": True, "article_ids": [20]},
            "sections": [],
            "componentes": [{"key": "lo_ultimo", "active": True, "article_ids": []}],
        }
        exclude = self._get_lo_ultimo_exclude_ids(resolved)
        self.assertIn(20, exclude)

    def test_recomendadas_excluded_from_lo_ultimo(self):
        """Articles in recomendadas (lv and domingo) must be excluded from Lo último."""
        resolved = {
            "principal":  {"active": True, "article_ids": []},
            "suplemento": {"active": True, "article_ids": []},
            "sections": [],
            "componentes": [
                {"key": "recomendadas_lv",      "active": True, "article_ids": [30]},
                {"key": "recomendadas_domingo",  "active": True, "article_ids": [31]},
                {"key": "lo_ultimo",             "active": True, "article_ids": []},
            ],
        }
        exclude = self._get_lo_ultimo_exclude_ids(resolved)
        self.assertIn(30, exclude)
        self.assertIn(31, exclude)

    def test_area_article_not_excluded_even_when_also_in_static_blocks(self):
        """
        Full scenario: principal=[1,2], suplemento=[3], area=[5,6].
        Lo último must exclude 1, 2, 3 but NOT 5 or 6.
        """
        resolved = {
            "principal":  {"active": True, "article_ids": [1, 2]},
            "suplemento": {"active": True, "article_ids": [3]},
            "especial":   {"active": True, "article_ids": []},
            "sections": [
                {"type": "publication", "slug": "deporte", "name": "Deporte",
                 "active": True, "article_ids": [5, 6]},
            ],
            "componentes": [
                {"key": "lo_ultimo", "active": True, "article_ids": []},
            ],
        }
        exclude = self._get_lo_ultimo_exclude_ids(resolved)
        self.assertIn(1, exclude)
        self.assertIn(2, exclude)
        self.assertIn(3, exclude)
        self.assertNotIn(5, exclude)
        self.assertNotIn(6, exclude)


class SortSectionsByRecencyTest(SimpleTestCase):
    """
    Tests that _sort_sections_by_recency orders sections by the date_published
    of their first article, most recent first, using a single DB query.
    Article is imported locally inside the function, so patch at core.models.Article.
    """

    def _dt(self, year, month, day):
        return datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)

    def _run(self, sections, dates_by_id):
        """Run _sort_sections_by_recency with a mocked Article queryset."""
        grid = {"sections": [dict(s) for s in sections]}
        with patch("core.models.Article") as mock_art:
            mock_art.objects.filter.return_value.values_list.return_value = list(dates_by_id.items())
            _sort_sections_by_recency(grid)
        return [s["slug"] for s in grid["sections"]]

    def test_sections_sorted_most_recent_first(self):
        """Sections are ordered by first article date, most recent first."""
        sections = [
            {"slug": "mundo",    "article_ids": [1]},
            {"slug": "deporte",  "article_ids": [2]},
            {"slug": "ambiente", "article_ids": [3]},
        ]
        dates = {
            1: self._dt(2026, 4, 20),  # mundo — oldest
            2: self._dt(2026, 4, 24),  # deporte — most recent
            3: self._dt(2026, 4, 22),  # ambiente — middle
        }
        result = self._run(sections, dates)
        self.assertEqual(result, ["deporte", "ambiente", "mundo"])

    def test_sections_without_articles_go_last(self):
        """Sections with no article_ids are placed at the end."""
        sections = [
            {"slug": "mundo",    "article_ids": []},
            {"slug": "deporte",  "article_ids": [1]},
        ]
        dates = {1: self._dt(2026, 4, 24)}
        result = self._run(sections, dates)
        self.assertEqual(result, ["deporte", "mundo"])

    def test_empty_sections_list_no_error(self):
        """Empty sections list returns without error."""
        result = self._run([], {})
        self.assertEqual(result, [])

    def test_uses_first_article_id_only(self):
        """Only the first article_id of each section determines the order."""
        sections = [
            {"slug": "a", "article_ids": [10, 99]},  # first=10: old, second=99: irrelevant
            {"slug": "b", "article_ids": [20, 88]},  # first=20: recent
        ]
        dates = {
            10: self._dt(2026, 4, 1),
            20: self._dt(2026, 4, 24),
        }
        result = self._run(sections, dates)
        self.assertEqual(result, ["b", "a"])

    def test_sections_with_same_date_preserve_relative_order(self):
        """Sections with identical first-article dates keep their original relative order."""
        sections = [
            {"slug": "a", "article_ids": [1]},
            {"slug": "b", "article_ids": [2]},
            {"slug": "c", "article_ids": [3]},
        ]
        same_date = self._dt(2026, 4, 20)
        dates = {1: same_date, 2: same_date, 3: same_date}
        result = self._run(sections, dates)
        self.assertEqual(result, ["a", "b", "c"])

    def test_all_sections_empty_no_error(self):
        """All sections with no article_ids — no error, original order preserved."""
        sections = [
            {"slug": "mundo",   "article_ids": []},
            {"slug": "cultura", "article_ids": []},
        ]
        result = self._run(sections, {})
        self.assertEqual(result, ["mundo", "cultura"])


class DeduplicateSignalTest(SimpleTestCase):
    """
    Tests for the pre_save signal _deduplicate_grid_data in apps.py.

    The signal must:
    - Skip when update_fields is set and does not include "grid_data"
    - Skip when grid_data is not a dict
    - Call resolve_layout_grid_data and update instance.grid_data when it runs
    """

    def _make_instance(self, grid_data):
        instance = MagicMock()
        instance.grid_data = grid_data
        return instance

    def test_skips_when_grid_data_not_in_update_fields(self):
        """Signal must not run when update_fields excludes grid_data (e.g. pending_grid_data save)."""
        instance = self._make_instance({"principal": {"active": True, "article_ids": [1]}})
        original = dict(instance.grid_data)
        _deduplicate_grid_data(sender=None, instance=instance,
                               update_fields=frozenset(["pending_grid_data"]))
        self.assertEqual(instance.grid_data, original)

    def test_runs_when_update_fields_is_none(self):
        """Signal must run when update_fields is None (full save)."""
        instance = self._make_instance({"principal": {"active": True, "article_ids": [1]}})
        resolved = {"principal": {"active": True, "article_ids": [1]}, "_resolved": True}
        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved):
            _deduplicate_grid_data(sender=None, instance=instance, update_fields=None)
        self.assertEqual(instance.grid_data, resolved)

    def test_runs_when_grid_data_in_update_fields(self):
        """Signal must run when update_fields explicitly includes grid_data."""
        instance = self._make_instance({"principal": {"active": True, "article_ids": [1]}})
        resolved = {"principal": {"active": True, "article_ids": [1]}, "_resolved": True}
        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved):
            _deduplicate_grid_data(sender=None, instance=instance,
                                   update_fields=frozenset(["grid_data", "modified"]))
        self.assertEqual(instance.grid_data, resolved)

    def test_skips_when_grid_data_not_a_dict(self):
        """Signal must not crash or modify grid_data when it is not a dict."""
        instance = self._make_instance([])  # invalid grid_data
        _deduplicate_grid_data(sender=None, instance=instance, update_fields=None)
        self.assertEqual(instance.grid_data, [])

    def test_signal_passes_dedup_populated_true(self):
        """Signal must call resolve_layout_grid_data with dedup_populated=True — this is
        what activates cross-block filtering of saved article_ids at persist time."""
        instance = self._make_instance({"principal": {"active": True, "article_ids": [1]}})
        with patch("homev4.views.resolve_layout_grid_data", return_value={}) as mock_resolve:
            _deduplicate_grid_data(sender=None, instance=instance, update_fields=None)
        _, kwargs = mock_resolve.call_args
        self.assertTrue(kwargs.get("dedup_populated"),
                        "Signal must pass dedup_populated=True to resolve_layout_grid_data")


# A known Saturday: weekday()=5 → extra_articles resolved from FSNewsletter
_SATURDAY = datetime.date(2026, 4, 25)  # weekday()=5

# The Sunday of the same weekend — shares the "Fin de semana" edition (date_published=Saturday)
_SUNDAY = datetime.date(2026, 4, 26)  # weekday()=6


class ResolveTodayGridDataExtraArticlesTest(SimpleTestCase):
    """
    Tests for extra_articles resolution in _resolve_today_grid_data on Saturdays.

    On Saturday the function must query FSNewsletter and populate extra_articles
    so the Preview 5am editor shows Pablo the correct content before he saves
    the pending_grid_data.
    """

    def _run(self, date, extra_article_ids=None):
        from homev4.views import _resolve_today_grid_data

        mock_layout = MagicMock()
        mock_layout.grid_data = {}

        mock_edition = MagicMock()
        mock_edition.top_articles = []

        with patch("homev4.views.HomeLayout") as mock_hl, \
             patch("homev4.views.Publication") as mock_pub, \
             patch("homev4.views.timezone") as mock_tz, \
             patch("homev4.views._fetch_source_articles_post_5am", return_value=[]), \
             patch("core.models.Edition") as mock_ed, \
             patch("homev4.views._fetch_extra_article_ids_for_preview",
                   return_value=list(extra_article_ids or [])):

            # HomeLayout.objects.filter → base layout
            mock_hl.objects.filter.return_value.first.return_value = mock_layout
            # Publication.objects.filter(slug="findesemana").first() → a mock pub (weekend path)
            mock_pub.objects.filter.return_value.first.return_value = MagicMock()
            mock_tz.localdate.return_value = date
            # Edition.objects.filter(...).order_by(...).first() → mock_edition (both weekday and weekend paths)
            mock_ed.objects.filter.return_value.order_by.return_value.first.return_value = mock_edition

            return _resolve_today_grid_data(MagicMock())

    def test_saturday_with_fsnewsletter_populates_extra_articles(self):
        """On Saturday, extra_articles is resolved from FSNewsletter when it exists."""
        result = self._run(_SATURDAY, extra_article_ids=[10, 20, 30])
        self.assertEqual(result.get("extra_articles", {}).get("article_ids"), [10, 20, 30])

    def test_saturday_fsnewsletter_missing_no_error(self):
        """On Saturday, if FSNewsletter doesn't exist (helper returns []) extra_articles is not set."""
        result = self._run(_SATURDAY, extra_article_ids=[])
        self.assertFalse(result.get("extra_articles", {}).get("article_ids"))

    def test_non_saturday_does_not_resolve_extra_articles(self):
        """On non-Saturday days, extra_articles is not resolved."""
        result = self._run(_MONDAY)
        self.assertNotIn("extra_articles", result)


class PropagateArticleIdsExtraTest(SimpleTestCase):
    """Tests that _propagate_article_ids includes extra_articles when syncing sibling layouts."""

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

    def test_extra_articles_propagated_to_sibling(self):
        """extra_articles IDs from source_grid are copied to sibling layouts."""
        result = self._run_propagate(
            source_grid={"extra_articles": {"article_ids": [10, 20]}},
            sibling_grid_data={"extra_articles": {"active": True, "article_ids": []}},
        )
        self.assertEqual(result["extra_articles"]["article_ids"], [10, 20])

    def test_extra_articles_preserves_sibling_active_flag(self):
        """Propagation only overwrites article_ids — the sibling's active flag is preserved."""
        result = self._run_propagate(
            source_grid={"extra_articles": {"article_ids": [10]}},
            sibling_grid_data={"extra_articles": {"active": False, "article_ids": []}},
        )
        self.assertFalse(result["extra_articles"]["active"])
        self.assertEqual(result["extra_articles"]["article_ids"], [10])


class ResolveTodayGridDataWeekendEditionTest(SimpleTestCase):
    """
    Tests for the weekend edition selection in _resolve_today_grid_data.

    On Saturday (weekday=5) and Sunday (weekday=6) there is no "la diaria" edition —
    the home principal block must come from the "Fin de semana" edition (publication
    slug "findesemana").  The edition is created once per weekend with
    date_published=Saturday and shared through Sunday, so the query uses
    .order_by("-date_published").first() WITHOUT a date_published=today filter
    (a strict date filter would miss the Saturday edition when opening the editor
    on Sunday).

    On weekdays the query filters by both publication=ladiaria and date_published=today.
    The findesemana publication is never queried on weekdays.

    Bugs to watch for:
    - Using date_published=today on Sunday → edition not found → empty principal.
    - Querying ladiaria on weekends → edition not found → empty principal.
    - Querying findesemana on weekdays → stale weekend articles in the weekday home.
    """

    def _run(self, date, edition_articles=None, fds_pub_exists=True):
        """
        Run _resolve_today_grid_data with all DB calls mocked.

        edition_articles: list of article IDs the mock edition exposes via top_articles.
                          None means the edition query returns None (no edition found).
        fds_pub_exists:   whether Publication.objects.filter(slug="findesemana").first()
                          returns a publication object (True) or None (False).
        Returns (grid_data, mock_pub, mock_ed) so callers can assert on call args.
        """
        from homev4.views import _resolve_today_grid_data

        mock_layout = MagicMock()
        mock_layout.grid_data = {}

        mock_edition = MagicMock()
        mock_edition.top_articles = [_art(i) for i in (edition_articles or [])]

        with patch("homev4.views.HomeLayout") as mock_hl, \
             patch("homev4.views.Publication") as mock_pub, \
             patch("homev4.views.timezone") as mock_tz, \
             patch("homev4.views._fetch_source_articles_post_5am", return_value=[]), \
             patch("core.models.Edition") as mock_ed, \
             patch("homev4.views._fetch_extra_article_ids_for_preview", return_value=[]):

            mock_hl.objects.filter.return_value.first.return_value = mock_layout
            mock_pub.objects.filter.return_value.first.return_value = MagicMock() if fds_pub_exists else None
            mock_tz.localdate.return_value = date
            # edition_articles=None simulates no edition found (first() returns None)
            first_val = mock_edition if edition_articles is not None else None
            mock_ed.objects.filter.return_value.order_by.return_value.first.return_value = first_val

            return _resolve_today_grid_data(MagicMock()), mock_pub, mock_ed

    def test_saturday_fetches_findesemana_edition(self):
        """On Saturday, principal_ids come from the most recent findesemana edition."""
        result, mock_pub, _ = self._run(_SATURDAY, edition_articles=[10, 20, 30])
        self.assertEqual(result["principal"]["article_ids"], [10, 20, 30])
        # Must resolve the findesemana publication, not assume the ladiaria publication
        mock_pub.objects.filter.assert_called_once_with(slug="findesemana")

    def test_sunday_fetches_findesemana_edition(self):
        """On Sunday, principal_ids also come from findesemana (no date_published=today filter).
        The edition has date_published=Saturday; a strict date=Sunday filter would miss it."""
        result, mock_pub, _ = self._run(_SUNDAY, edition_articles=[40, 50])
        self.assertEqual(result["principal"]["article_ids"], [40, 50])
        mock_pub.objects.filter.assert_called_once_with(slug="findesemana")

    def test_saturday_findesemana_pub_missing_gives_empty_principal(self):
        """If the findesemana publication row doesn't exist, principal is empty — no crash.
        Regression guard: Publication.objects.filter().first() returning None must be
        handled gracefully (the edition query is skipped via 'if fds_pub else None')."""
        result, _, _ = self._run(_SATURDAY, fds_pub_exists=False)
        self.assertEqual(result["principal"]["article_ids"], [])

    def test_saturday_no_findesemana_edition_gives_empty_principal(self):
        """If findesemana pub exists but has no editions yet, principal is empty — no crash.
        Happens if Pablo hasn't created the weekend edition when the editor is first opened."""
        result, _, _ = self._run(_SATURDAY, edition_articles=None, fds_pub_exists=True)
        self.assertEqual(result["principal"]["article_ids"], [])

    def test_weekday_does_not_query_findesemana(self):
        """On weekdays, findesemana publication is never queried — only ladiaria is used.
        Regression guard: the weekday >= 5 branch must not accidentally fire on weekdays,
        which would inject stale weekend articles into the weekday home."""
        result, mock_pub, _ = self._run(_MONDAY, edition_articles=[1, 2])
        mock_pub.objects.filter.assert_not_called()
        self.assertEqual(result["principal"]["article_ids"], [1, 2])
