"""
Unit tests for the Humor and Crucigrama blocks in homev4.

Covers:
- COMPONENT_DEFINITIONS and BLOCK_ARTICLE_LIMITS declarations
- _fetch_component_articles("humor"): saved fallback, section fallback, missing section
- resolve_layout_grid_data: humor is NOT in _RESOLVE_SKIP_KEYS (resolved + deduped)
- _clear_fallback_blocks: humor is NOT cleared (manual selection persists); crucigrama is not
- build_home_data: humor articles via default branch; crucigrama crossword fields
- crucigrama is in _RESOLVE_SKIP_KEYS (skipped by resolver)
- Graceful degradation when utopia_cms_ladiaria is not installed (crucigrama ImportError)

All DB calls are mocked — no database required. Tests run with SimpleTestCase.
"""
import datetime
import sys
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings


def _art(article_id):
    """Minimal mock Article with only an id attribute."""
    a = MagicMock()
    a.id = article_id
    return a


def _make_published_mock(available_ids):
    """
    Return a mock for Article.published that returns _art() objects for the
    requested id__in subset, preserving available_ids order.
    """
    articles = {i: _art(i) for i in available_ids}

    class FakeQS:
        def __init__(self, ids):
            self._ids = list(ids)

        def filter(self, **kwargs):
            id__in = list(kwargs.get("id__in", []))
            return FakeQS([i for i in self._ids if i in id__in])

        def select_related(self, *args):
            return self

        def __iter__(self):
            return (articles[i] for i in self._ids if i in articles)

    return FakeQS(available_ids)


# ---------------------------------------------------------------------------
# COMPONENT_DEFINITIONS and BLOCK_ARTICLE_LIMITS
# ---------------------------------------------------------------------------

class ComponentDefinitionsTest(SimpleTestCase):
    """Verifies humor and crucigrama are registered correctly."""

    def test_humor_in_component_definitions(self):
        """humor must be present in COMPONENT_DEFINITIONS with replace_mode=True."""
        from homev4.views import COMPONENT_DEFINITIONS
        keys = {d["key"]: d for d in COMPONENT_DEFINITIONS}
        self.assertIn("humor", keys)
        self.assertTrue(keys["humor"].get("replace_mode"))

    def test_crucigrama_in_component_definitions(self):
        """crucigrama must be present in COMPONENT_DEFINITIONS with no_articles=True."""
        from homev4.views import COMPONENT_DEFINITIONS
        keys = {d["key"]: d for d in COMPONENT_DEFINITIONS}
        self.assertIn("crucigrama", keys)
        self.assertTrue(keys["crucigrama"].get("no_articles"))

    def test_humor_block_article_limit_is_one(self):
        """Humor picker must be capped at 1 article."""
        from homev4.views import BLOCK_ARTICLE_LIMITS
        self.assertEqual(BLOCK_ARTICLE_LIMITS["humor"], 1)

    def test_crucigrama_not_in_block_article_limits(self):
        """Crucigrama has no article limit (no_articles block)."""
        from homev4.views import BLOCK_ARTICLE_LIMITS
        self.assertNotIn("crucigrama", BLOCK_ARTICLE_LIMITS)

    def test_crucigrama_in_resolve_skip_keys(self):
        """Crucigrama must be in _RESOLVE_SKIP_KEYS so the resolver never touches it."""
        from homev4.views import _RESOLVE_SKIP_KEYS
        self.assertIn("crucigrama", _RESOLVE_SKIP_KEYS)

    def test_humor_not_in_resolve_skip_keys(self):
        """Humor must NOT be in _RESOLVE_SKIP_KEYS — it is resolved and deduplicated."""
        from homev4.views import _RESOLVE_SKIP_KEYS
        self.assertNotIn("humor", _RESOLVE_SKIP_KEYS)


# ---------------------------------------------------------------------------
# _fetch_component_articles("humor")
# ---------------------------------------------------------------------------

class FetchHumorArticlesTest(SimpleTestCase):
    """
    Unit tests for _fetch_component_articles("humor").

    Contract:
    - saved_ids non-empty → return those articles (like le_monde / lento).
    - saved_ids empty → fetch the latest article from the Section with slug "humor".
    - HOMEV4_HUMOR_SECTION_SLUG setting overrides the default slug.
    - Section.DoesNotExist → return [], log warning, no crash.
    - Saved ID not in Article.published → silently dropped.
    """

    def _call(self, saved_ids=None, section_articles=None, section_exists=True, slug="humor"):
        from homev4.views import _fetch_component_articles

        mock_section = MagicMock()
        mock_section.latest.return_value = section_articles or []

        def section_get(**kwargs):
            if section_exists:
                return mock_section
            from core.models import Section
            raise Section.DoesNotExist

        with patch("homev4.views.Section") as mock_sec, \
             patch("homev4.views.Article") as mock_art:
            mock_sec.objects.get.side_effect = section_get
            mock_art.published = _make_published_mock(
                [a.id for a in (saved_ids or [])] if saved_ids else []
            )
            return _fetch_component_articles(
                "humor",
                saved_ids=list(saved_ids or []),
            )

    def _call_with_published(self, saved_ids, available_ids):
        """Call with explicit published pool (for testing unpublished-drop behaviour)."""
        from homev4.views import _fetch_component_articles

        with patch("homev4.views.Section"), \
             patch("homev4.views.Article") as mock_art:
            mock_art.published = _make_published_mock(available_ids)
            return _fetch_component_articles("humor", saved_ids=list(saved_ids))

    def test_saved_ids_returned_directly(self):
        """When saved_ids is set, those articles are returned without touching the section."""
        from homev4.views import _fetch_component_articles

        mock_section = MagicMock()

        with patch("homev4.views.Section") as mock_sec, \
             patch("homev4.views.Article") as mock_art:
            mock_art.published = _make_published_mock([42])
            result = _fetch_component_articles("humor", saved_ids=[42])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 42)
        mock_sec.objects.get.assert_not_called()

    def test_fallback_fetches_from_section(self):
        """When no saved_ids, fetches the latest article from the humor section."""
        from homev4.views import _fetch_component_articles

        article = _art(99)
        mock_section = MagicMock()
        mock_section.latest.return_value = [article]

        with patch("homev4.views.Section") as mock_sec, \
             patch("homev4.views.Article"):
            mock_sec.objects.get.return_value = mock_section
            result = _fetch_component_articles("humor", saved_ids=[])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 99)
        mock_section.latest.assert_called_once_with(limit=1)

    def test_fallback_uses_default_slug(self):
        """Fallback section lookup uses slug 'humor' by default."""
        from homev4.views import _fetch_component_articles

        mock_section = MagicMock()
        mock_section.latest.return_value = []

        with patch("homev4.views.Section") as mock_sec, \
             patch("homev4.views.Article"):
            mock_sec.objects.get.return_value = mock_section
            _fetch_component_articles("humor", saved_ids=[])

        mock_sec.objects.get.assert_called_once_with(slug="humor")

    @override_settings(HOMEV4_HUMOR_SECTION_SLUG="mi-humor")
    def test_custom_slug_from_settings(self):
        """HOMEV4_HUMOR_SECTION_SLUG overrides the default slug."""
        from homev4.views import _fetch_component_articles

        mock_section = MagicMock()
        mock_section.latest.return_value = []

        with patch("homev4.views.Section") as mock_sec, \
             patch("homev4.views.Article"):
            mock_sec.objects.get.return_value = mock_section
            _fetch_component_articles("humor", saved_ids=[])

        mock_sec.objects.get.assert_called_once_with(slug="mi-humor")

    def test_section_not_found_returns_empty(self):
        """Section.DoesNotExist → return [], no crash."""
        from homev4.views import _fetch_component_articles
        from core.models import Section as RealSection

        with patch("homev4.views.Section") as mock_sec, \
             patch("homev4.views.Article"):
            # DoesNotExist must be the real exception class so except can catch it.
            mock_sec.DoesNotExist = RealSection.DoesNotExist
            mock_sec.objects.get.side_effect = RealSection.DoesNotExist
            result = _fetch_component_articles("humor", saved_ids=[])

        self.assertEqual(result, [])

    def test_saved_id_not_published_is_dropped(self):
        """A saved article ID not in Article.published is silently dropped."""
        result = self._call_with_published(saved_ids=[10, 20], available_ids=[10])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 10)

    def test_all_saved_ids_unpublished_returns_empty(self):
        """All saved IDs unpublished → return []."""
        result = self._call_with_published(saved_ids=[10, 20], available_ids=[])
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _clear_fallback_blocks
# ---------------------------------------------------------------------------

class ClearFallbackBlocksTest(SimpleTestCase):
    """
    humor must NOT be cleared — manual editor selection persists across refreshes.
    crucigrama must NOT be cleared (it is in _RESOLVE_SKIP_KEYS, not a fallback block).
    """

    def _call(self, grid_data):
        from homev4.views import _clear_fallback_blocks
        return _clear_fallback_blocks(grid_data)

    def test_humor_article_ids_not_cleared(self):
        """humor article_ids are preserved so the manual editor selection persists."""
        grid = {"componentes": [{"key": "humor", "active": True, "article_ids": [42]}]}
        result = self._call(grid)
        humor = next(c for c in result["componentes"] if c["key"] == "humor")
        self.assertEqual(humor["article_ids"], [42])

    def test_humor_active_flag_preserved(self):
        """humor active flag is preserved regardless."""
        grid = {"componentes": [{"key": "humor", "active": False, "article_ids": [42]}]}
        result = self._call(grid)
        humor = next(c for c in result["componentes"] if c["key"] == "humor")
        self.assertFalse(humor["active"])

    def test_crucigrama_not_cleared(self):
        """crucigrama is in _RESOLVE_SKIP_KEYS, not a fallback block — never touched."""
        grid = {"componentes": [{"key": "crucigrama", "active": True, "article_ids": []}]}
        result = self._call(grid)
        crucigrama = next(c for c in result["componentes"] if c["key"] == "crucigrama")
        # active flag must be preserved; no crash; no modification attempted
        self.assertTrue(crucigrama["active"])


# ---------------------------------------------------------------------------
# resolve_layout_grid_data with humor
# ---------------------------------------------------------------------------

class ResolveHumorTest(SimpleTestCase):
    """
    humor is NOT in _RESOLVE_SKIP_KEYS, so resolve_layout_grid_data fills its
    article_ids when empty and deduplicates when dedup_populated=True.
    """

    def _run(self, grid_data, fetch_humor_ids=(), dedup_populated=False):
        from homev4.views import resolve_layout_grid_data

        def mock_fetch(key, saved_ids=None, exclude_ids=None, **kwargs):
            if key == "humor":
                pool = [_art(i) for i in fetch_humor_ids]
                return [a for a in pool if a.id not in (exclude_ids or set())]
            return []

        with patch("homev4.views.get_current_edition") as mock_ed, \
             patch("homev4.views._fetch_source_articles", return_value=[]), \
             patch("homev4.views._fetch_area_articles", return_value=[]), \
             patch("homev4.views._fetch_component_articles", side_effect=mock_fetch), \
             patch("homev4.views.timezone") as mock_tz:
            mock_ed.return_value.top_articles = []
            mock_tz.localdate.return_value = __import__("datetime").date(2026, 5, 13)
            mock_tz.now.return_value = MagicMock()
            return resolve_layout_grid_data(grid_data, dedup_populated=dedup_populated)

    def test_empty_humor_filled_from_section(self):
        """Empty humor article_ids are filled via _fetch_component_articles fallback."""
        grid = {"componentes": [{"key": "humor", "active": True, "article_ids": []}]}
        result = self._run(grid, fetch_humor_ids=(99,))
        humor = next(c for c in result["componentes"] if c["key"] == "humor")
        self.assertEqual(humor["article_ids"], [99])

    def test_saved_humor_ids_preserved_without_dedup(self):
        """Without dedup_populated, saved humor article_ids are kept as-is."""
        grid = {"componentes": [{"key": "humor", "active": True, "article_ids": [42]}]}
        result = self._run(grid, fetch_humor_ids=(99,))
        humor = next(c for c in result["componentes"] if c["key"] == "humor")
        self.assertEqual(humor["article_ids"], [42])

    def test_humor_deduped_when_overlaps_principal(self):
        """dedup_populated=True: humor article already in principal is removed."""
        grid = {
            "principal": {"active": True, "article_ids": [1, 2]},
            "componentes": [{"key": "humor", "active": True, "article_ids": [2]}],
        }
        result = self._run(grid, dedup_populated=True)
        humor = next(c for c in result["componentes"] if c["key"] == "humor")
        self.assertNotIn(2, humor["article_ids"])

    def test_inactive_humor_not_resolved(self):
        """Inactive humor component is skipped by the resolver."""
        grid = {"componentes": [{"key": "humor", "active": False, "article_ids": []}]}
        result = self._run(grid, fetch_humor_ids=(99,))
        humor = next(c for c in result["componentes"] if c["key"] == "humor")
        self.assertEqual(humor["article_ids"], [])


# ---------------------------------------------------------------------------
# build_home_data — humor
# ---------------------------------------------------------------------------

class BuildHomeDataHumorTest(SimpleTestCase):
    """
    Tests for the humor component inside build_home_data.

    Humor goes through the default else-branch: reads article_ids from resolved
    grid_data and fetches articles by ID from Article.published.
    """

    def _build(self, humor_ids, available_ids=None):
        from homev4.views import build_home_data

        if available_ids is None:
            available_ids = list(humor_ids)

        resolved_grid = {
            "principal":  {"active": True, "article_ids": []},
            "suplemento": {"active": True, "article_ids": []},
            "sections": [],
            "componentes": [
                {"key": "humor", "active": True, "article_ids": list(humor_ids)},
            ],
        }

        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved_grid), \
             patch("homev4.views.Article") as mock_art, \
             patch("homev4.views._fetch_component_articles", return_value=[]), \
             patch("homev4.views._block_active", side_effect=lambda _k, v: bool(v)), \
             patch("homev4.views._SUPLEMENTO_SOURCE_BY_WEEKDAY", {}), \
             patch("homev4.views.timezone") as mock_tz:
            mock_art.published = _make_published_mock(available_ids)
            mock_tz.localdate.return_value = __import__("datetime").date(2026, 5, 13)
            mock_tz.now.return_value = MagicMock()
            result = build_home_data(resolved_grid)

        return next((c for c in result["componentes"] if c["key"] == "humor"), None)

    def test_humor_articles_populated_from_saved_ids(self):
        """build_home_data reads humor article_ids and returns the corresponding articles."""
        comp = self._build(humor_ids=[42])
        self.assertIsNotNone(comp)
        self.assertEqual([a.id for a in comp["articles"]], [42])

    def test_humor_empty_ids_returns_empty_articles(self):
        """When humor article_ids is [], articles is []."""
        comp = self._build(humor_ids=[])
        self.assertEqual(comp["articles"], [])

    def test_humor_unpublished_article_dropped(self):
        """Article in humor article_ids that is not in Article.published is dropped."""
        comp = self._build(humor_ids=[10, 20], available_ids=[10])
        self.assertEqual([a.id for a in comp["articles"]], [10])

    def test_humor_order_preserved(self):
        """Articles are returned in article_ids order, not DB order."""
        comp = self._build(humor_ids=[30, 10, 20], available_ids=[10, 20, 30])
        self.assertEqual([a.id for a in comp["articles"]], [30, 10, 20])


# ---------------------------------------------------------------------------
# build_home_data — crucigrama
# ---------------------------------------------------------------------------

class BuildHomeDataCrucigramaTest(SimpleTestCase):
    """
    Tests for the crucigrama component inside build_home_data.

    Two paths:
    A) Pre-computed: crossword_id already stored in the comp entry by the signal.
       build_home_data reads from grid_data with no DB query.
    B) Fallback: comp has no crossword_id yet (old layout); queries DB directly.

    Contract:
    - articles is always [].
    - crossword_id / crossword_image_url / crossword_url come from the comp entry
      when pre-computed, or from Crossword.objects.first() as fallback.
    - When Crossword.objects.first() returns None → no crossword fields added.
    - When utopia_cms_ladiaria is not installed (ImportError) → no crash, no fields.
    """

    def _build(self, comp_entry=None, crossword=None, import_error=False):
        """
        comp_entry: dict merged into the crucigrama comp (simulates pre-computed data).
        crossword:  Crossword mock returned by DB fallback (used when comp has no crossword_id).
        import_error: simulate utopia_cms_ladiaria not installed for the DB fallback path.
        """
        from homev4.views import build_home_data

        cruci_comp = {"key": "crucigrama", "active": True}
        if comp_entry:
            cruci_comp.update(comp_entry)

        resolved_grid = {
            "principal":  {"active": True, "article_ids": []},
            "suplemento": {"active": True, "article_ids": []},
            "sections": [],
            "componentes": [cruci_comp],
        }

        def _run():
            with patch("homev4.views.resolve_layout_grid_data", return_value=resolved_grid), \
                 patch("homev4.views.Article") as mock_art, \
                 patch("homev4.views._fetch_component_articles", return_value=[]), \
                 patch("homev4.views._block_active", side_effect=lambda _k, v: bool(v)), \
                 patch("homev4.views._SUPLEMENTO_SOURCE_BY_WEEKDAY", {}), \
                 patch("homev4.views.timezone") as mock_tz:
                mock_art.published = _make_published_mock([])
                mock_tz.localdate.return_value = __import__("datetime").date(2026, 5, 13)
                mock_tz.now.return_value = MagicMock()
                return build_home_data(resolved_grid)

        if import_error:
            # Setting a key to None in sys.modules makes Python raise ImportError on import.
            with patch.dict(sys.modules, {"utopia_cms_ladiaria": None, "utopia_cms_ladiaria.models": None}):
                result = _run()
        else:
            fake_mod = MagicMock()
            fake_mod.Crossword.objects.first.return_value = crossword
            with patch.dict(sys.modules, {"utopia_cms_ladiaria.models": fake_mod}):
                result = _run()

        return next((c for c in result["componentes"] if c["key"] == "crucigrama"), None)

    def _make_crossword(self, cw_id=7, has_image=True):
        cw = MagicMock()
        cw.id = cw_id
        cw.date_published = datetime.date(2026, 1, 5)  # Monday — date_format needs a real date
        if has_image:
            cw.image.url = f"/media/crossword/img/{cw_id}.png"
        else:
            cw.image = None
        return cw

    # ── Path A: pre-computed from comp entry ──────────────────────────────────

    def test_precomputed_articles_always_empty(self):
        """crucigrama never has articles regardless of which path is taken."""
        comp = self._build(comp_entry={"crossword_id": 5, "crossword_image_url": "/img/5.png", "crossword_url": "/crucigramas/"})
        self.assertEqual(comp["articles"], [])

    def test_precomputed_fields_read_from_comp_entry(self):
        """When crossword_id is in the comp entry, fields come from there — no DB query."""
        comp = self._build(comp_entry={"crossword_id": 5, "crossword_image_url": "/img/5.png", "crossword_url": "/crucigramas/"})
        self.assertEqual(comp["crossword_id"], 5)
        self.assertEqual(comp["crossword_image_url"], "/img/5.png")
        self.assertEqual(comp["crossword_url"], "/crucigramas/")

    def test_precomputed_no_image_url_is_none(self):
        """Pre-computed image_url can be None when the crossword has no image."""
        comp = self._build(comp_entry={"crossword_id": 5, "crossword_image_url": None, "crossword_url": "/crucigramas/"})
        self.assertIsNone(comp["crossword_image_url"])

    def test_precomputed_missing_url_defaults_to_crucigramas(self):
        """crossword_url falls back to /crucigramas/ if absent in the comp entry."""
        comp = self._build(comp_entry={"crossword_id": 5, "crossword_image_url": None})
        self.assertEqual(comp["crossword_url"], "/crucigramas/")

    # ── Path B: DB fallback (comp has no crossword_id yet) ───────────────────

    def test_fallback_crossword_fields_set_when_available(self):
        """When no pre-computed data, fields come from Crossword.objects.first()."""
        cw = self._make_crossword(cw_id=7, has_image=True)
        comp = self._build(crossword=cw)
        self.assertEqual(comp["crossword_id"], 7)
        self.assertEqual(comp["crossword_image_url"], "/media/crossword/img/7.png")
        self.assertEqual(comp["crossword_url"], "/crucigramas/")

    def test_fallback_no_image_url_is_none(self):
        """DB fallback: crossword_image_url is None when crossword has no image."""
        cw = self._make_crossword(has_image=False)
        comp = self._build(crossword=cw)
        self.assertIsNone(comp["crossword_image_url"])

    def test_fallback_no_crossword_object_no_fields(self):
        """DB fallback: when Crossword.objects.first() returns None, no fields added."""
        comp = self._build(crossword=None)
        self.assertNotIn("crossword_id", comp)
        self.assertNotIn("crossword_image_url", comp)
        self.assertNotIn("crossword_url", comp)

    def test_fallback_import_error_no_crash(self):
        """DB fallback: when utopia_cms_ladiaria is not installed, no crash, no fields."""
        comp = self._build(import_error=True)
        self.assertIsNotNone(comp)
        self.assertEqual(comp["articles"], [])
        self.assertNotIn("crossword_id", comp)


# ---------------------------------------------------------------------------
# _update_crossword_in_layouts signal handler
# ---------------------------------------------------------------------------

class UpdateCrosswordInLayoutsTest(SimpleTestCase):
    """
    Tests for the Crossword post_save signal handler in apps.py.

    Contract:
    - Writes crossword_id, crossword_image_url, crossword_url into the crucigrama
      comp entry of every HomeLayout that has a crucigrama component.
    - Layouts without a crucigrama component are not touched.
    - Layouts with no grid_data dict are skipped without crashing.
    - Uses bulk_update so pre_save dedup does not re-run.
    """

    def _call(self, layouts, crossword):
        from homev4.apps import _update_crossword_in_layouts

        mock_qs = MagicMock()
        mock_qs.__iter__ = lambda s: iter(layouts)

        # Patch HomeLayout in homev4.models since the handler imports it from there.
        with patch("homev4.models.HomeLayout") as mock_model:
            mock_model.objects.all.return_value = mock_qs
            _update_crossword_in_layouts(sender=None, instance=crossword)
            return mock_model.objects.bulk_update.call_args

    def _make_layout(self, componentes):
        layout = MagicMock()
        layout.grid_data = {"componentes": componentes, "principal": {"article_ids": []}}
        return layout

    def _make_crossword(self, cw_id=10, has_image=True):
        cw = MagicMock()
        cw.id = cw_id
        cw.date_published = datetime.date(2026, 1, 5)  # Monday — date_format needs a real date
        if has_image:
            cw.image.url = f"/media/cw/{cw_id}.png"
        else:
            cw.image = None
        return cw

    def test_crucigrama_comp_updated(self):
        """Layout with crucigrama gets crossword fields written into the comp entry."""
        layout = self._make_layout([{"key": "crucigrama", "active": True}])
        cw = self._make_crossword(cw_id=10)
        self._call([layout], cw)
        cruci = next(c for c in layout.grid_data["componentes"] if c["key"] == "crucigrama")
        self.assertEqual(cruci["crossword_id"], 10)
        self.assertEqual(cruci["crossword_image_url"], "/media/cw/10.png")
        self.assertEqual(cruci["crossword_url"], "/crucigramas/")

    def test_no_image_writes_none(self):
        """When crossword has no image, crossword_image_url is written as None."""
        layout = self._make_layout([{"key": "crucigrama", "active": True}])
        cw = self._make_crossword(has_image=False)
        self._call([layout], cw)
        cruci = next(c for c in layout.grid_data["componentes"] if c["key"] == "crucigrama")
        self.assertIsNone(cruci["crossword_image_url"])

    def test_layout_without_crucigrama_not_updated(self):
        """Layout whose componentes don't include crucigrama is not added to bulk_update."""
        layout = self._make_layout([{"key": "opinion", "active": True}])
        cw = self._make_crossword()
        call_args = self._call([layout], cw)
        # bulk_update should not be called — nothing to update
        self.assertIsNone(call_args)

    def test_layout_with_invalid_grid_data_skipped(self):
        """Layout with non-dict grid_data is skipped without crashing."""
        layout = MagicMock()
        layout.grid_data = None
        cw = self._make_crossword()
        call_args = self._call([layout], cw)
        self.assertIsNone(call_args)

    def test_bulk_update_called_with_grid_data_field(self):
        """bulk_update is called with ['grid_data'] to avoid triggering pre_save signals."""
        layout = self._make_layout([{"key": "crucigrama", "active": True}])
        cw = self._make_crossword()
        call_args = self._call([layout], cw)
        self.assertIsNotNone(call_args)
        # call_args.args = (to_update_list, fields_list)
        updated_layouts, fields = call_args.args
        self.assertIn(layout, updated_layouts)
        self.assertEqual(fields, ["grid_data"])
