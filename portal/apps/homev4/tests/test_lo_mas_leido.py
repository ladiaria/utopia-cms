"""
Unit tests for the lo_mas_leido block.

Two surfaces under test:

1. update_lo_mas_leido_in_layouts() — called by sync_article_views after writing
   ArticleViews to MariaDB. Responsible for persisting the top-5 article IDs into
   HomeLayout.grid_data so the home can read them without a live DB query.

2. build_home_data() for the lo_mas_leido component — reads article_ids from the
   component entry saved by update_lo_mas_leido_in_layouts, with a fallback to
   _fetch_component_articles when the block has not been populated yet.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.
"""
import datetime
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase


def _art(article_id):
    """Minimal mock Article with only an id attribute."""
    a = MagicMock()
    a.id = article_id
    return a


def _make_published_mock(available_ids):
    """
    Return a mock for Article.published whose .filter(...).select_related(...)
    returns a list of _art() objects for the requested id__in subset.
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

        def prefetch_related(self, *args):
            return self

        def __iter__(self):
            return (articles[i] for i in self._ids if i in articles)

    return FakeQS(available_ids)


# ---------------------------------------------------------------------------
# update_lo_mas_leido_in_layouts
# ---------------------------------------------------------------------------

class UpdateLoMasLeidoInLayoutsTest(SimpleTestCase):
    """
    Tests for update_lo_mas_leido_in_layouts().

    Invariants:
    - mas_leidos exception → return immediately, no layout touched.
    - mas_leidos returns [] → return immediately, no layout touched.
    - IDs unchanged → layout.save not called (avoid spurious writes).
    - IDs changed → layout.save called with update_fields, audit log written.
    - layout without lo_mas_leido component → no crash, no save.
    - layout.grid_data not a dict → treated as {} without crash.
    - Multiple layouts: each one that needs updating is saved independently.
    """

    def _run(self, mas_leidos_result, layouts, mas_leidos_raises=False):
        """
        Run update_lo_mas_leido_in_layouts with fully mocked dependencies.

        mas_leidos_result: list of IDs returned by mas_leidos(), or ignored if raises.
        layouts: list of mock HomeLayout objects (each has .grid_data and .save).
        mas_leidos_raises: if True, mas_leidos raises RuntimeError.
        """
        from homev4.views import update_lo_mas_leido_in_layouts

        mock_pub = MagicMock()
        qs_mock = MagicMock()
        qs_mock.__iter__ = MagicMock(return_value=iter(layouts))

        mas_mock = MagicMock(
            side_effect=RuntimeError("db down") if mas_leidos_raises else None,
            return_value=mas_leidos_result,
        )

        with patch("homev4.views.get_default_publication", return_value=mock_pub), \
             patch("homev4.views.HomeLayout") as mock_hl, \
             patch("homev4.views._write_audit_log") as mock_audit, \
             patch("core.views.masleidos.mas_leidos", mas_mock, create=True), \
             patch("homev4.views.update_lo_mas_leido_in_layouts.__globals__",
                   {**__import__("homev4.views", fromlist=["update_lo_mas_leido_in_layouts"]).__dict__}):

            mock_hl.objects.filter.return_value = qs_mock

            # Patch the import inside the function body.
            with patch.dict("sys.modules", {"core.views.masleidos": MagicMock(mas_leidos=mas_mock)}):
                update_lo_mas_leido_in_layouts()

        return mock_audit

    def _layout_with_ids(self, article_ids):
        """Return a mock layout whose lo_mas_leido component has the given article_ids."""
        layout = MagicMock()
        layout.grid_data = {
            "componentes": [{"key": "lo_mas_leido", "active": True, "article_ids": list(article_ids)}]
        }
        return layout

    def _layout_without_component(self):
        """Return a mock layout with no lo_mas_leido component."""
        layout = MagicMock()
        layout.grid_data = {"componentes": [{"key": "opinion", "active": True, "article_ids": []}]}
        return layout

    def _layout_non_dict_grid(self):
        """Return a mock layout whose grid_data is not a dict."""
        layout = MagicMock()
        layout.grid_data = None
        return layout

    def _call(self, mas_leidos_ids, layouts, mas_leidos_raises=False):
        """Simpler runner that patches mas_leidos at the import site inside the function."""
        from homev4.views import update_lo_mas_leido_in_layouts

        mock_pub = MagicMock()
        qs_mock = MagicMock()
        qs_mock.__iter__ = MagicMock(return_value=iter(layouts))

        mas_mock = MagicMock(
            side_effect=RuntimeError("db down") if mas_leidos_raises else None,
            return_value=mas_leidos_ids,
        )

        with patch("homev4.views.get_default_publication", return_value=mock_pub), \
             patch("homev4.views.HomeLayout") as mock_hl, \
             patch("homev4.views._write_audit_log") as mock_audit:

            mock_hl.objects.filter.return_value = qs_mock

            with patch("core.views.masleidos", create=True) as mas_mod:
                mas_mod.mas_leidos = mas_mock
                # The function does `from core.views.masleidos import mas_leidos` inside,
                # so patch sys.modules to intercept.
                import sys
                fake_module = MagicMock()
                fake_module.mas_leidos = mas_mock
                old = sys.modules.get("core.views.masleidos")
                sys.modules["core.views.masleidos"] = fake_module
                try:
                    update_lo_mas_leido_in_layouts()
                finally:
                    if old is None:
                        sys.modules.pop("core.views.masleidos", None)
                    else:
                        sys.modules["core.views.masleidos"] = old

        return mock_audit, mock_hl

    def test_mas_leidos_exception_does_not_save_layouts(self):
        """If mas_leidos raises, no layout is touched."""
        layout = self._layout_with_ids([1, 2, 3])
        audit, mock_hl = self._call([], [layout], mas_leidos_raises=True)
        layout.save.assert_not_called()
        audit.assert_not_called()

    def test_mas_leidos_empty_does_not_save_layouts(self):
        """If mas_leidos returns [], function exits early without saving any layout."""
        layout = self._layout_with_ids([1, 2, 3])
        audit, mock_hl = self._call([], [layout])
        layout.save.assert_not_called()
        audit.assert_not_called()

    def test_ids_unchanged_does_not_save(self):
        """If the layout already has the same IDs, layout.save is NOT called."""
        ids = [10, 20, 30]
        layout = self._layout_with_ids(ids)
        audit, _ = self._call(ids, [layout])
        layout.save.assert_not_called()
        audit.assert_not_called()

    def test_ids_changed_saves_layout(self):
        """When IDs differ from what's stored, layout.save is called with update_fields."""
        layout = self._layout_with_ids([1, 2])
        audit, _ = self._call([10, 20, 30], [layout])
        layout.save.assert_called_once_with(update_fields=["grid_data", "modified"])

    def test_ids_changed_writes_audit_log(self):
        """When IDs are updated, _write_audit_log is called with triggered_by='sync_article_views'."""
        layout = self._layout_with_ids([1, 2])
        audit, _ = self._call([10, 20, 30], [layout])
        self.assertEqual(audit.call_count, 1)
        args = audit.call_args[0]
        self.assertEqual(args[3], "sync_article_views")

    def test_ids_updated_in_component(self):
        """After calling, the component's article_ids must equal the new IDs list."""
        layout = self._layout_with_ids([1, 2])
        self._call([10, 20, 30], [layout])
        comp = next(c for c in layout.grid_data["componentes"] if c["key"] == "lo_mas_leido")
        self.assertEqual(comp["article_ids"], [10, 20, 30])

    def test_layout_without_lo_mas_leido_component_is_not_saved(self):
        """A layout with no lo_mas_leido component is not modified or saved."""
        layout = self._layout_without_component()
        audit, _ = self._call([10, 20, 30], [layout])
        layout.save.assert_not_called()
        audit.assert_not_called()

    def test_non_dict_grid_data_treated_as_empty(self):
        """A layout whose grid_data is not a dict is treated as {} — no crash, no save."""
        layout = self._layout_non_dict_grid()
        audit, _ = self._call([10, 20, 30], [layout])
        layout.save.assert_not_called()

    def test_only_changed_layouts_are_saved(self):
        """With two layouts, only the one with different IDs is saved."""
        new_ids = [10, 20, 30]
        layout_same = self._layout_with_ids(new_ids)     # already up-to-date
        layout_diff = self._layout_with_ids([1, 2, 3])   # needs update
        self._call(new_ids, [layout_same, layout_diff])
        layout_same.save.assert_not_called()
        layout_diff.save.assert_called_once()

    def test_multiple_layouts_all_updated_when_stale(self):
        """With two stale layouts, both are saved and audit-logged."""
        new_ids = [10, 20, 30]
        layout_a = self._layout_with_ids([1])
        layout_b = self._layout_with_ids([2])
        audit, _ = self._call(new_ids, [layout_a, layout_b])
        layout_a.save.assert_called_once()
        layout_b.save.assert_called_once()
        self.assertEqual(audit.call_count, 2)


# ---------------------------------------------------------------------------
# build_home_data — lo_mas_leido path
# ---------------------------------------------------------------------------

class BuildHomeDataLoMasLeidoTest(SimpleTestCase):
    """
    Tests for the lo_mas_leido branch inside build_home_data.

    Contract:
    - article_ids non-empty → read articles from DB by ID, preserve order, do NOT
      call _fetch_component_articles.
    - article_ids empty → call _fetch_component_articles as fallback.
    - Unpublished/deleted articles (not in Article.published) are silently dropped.
    - Order of returned articles matches article_ids order, not DB return order.
    """

    def _build(self, lo_mas_leido_ids, available_ids=None, fetch_fallback_articles=None):
        """
        Run build_home_data with a resolved grid containing one lo_mas_leido component.

        lo_mas_leido_ids: article_ids stored in the component (may be empty).
        available_ids: IDs that Article.published contains (defaults to lo_mas_leido_ids).
        fetch_fallback_articles: what _fetch_component_articles returns when called as fallback.

        Returns the component entry dict for lo_mas_leido from the result.
        """
        if available_ids is None:
            available_ids = list(lo_mas_leido_ids)

        resolved_grid = {
            "principal":  {"active": True, "article_ids": []},
            "suplemento": {"active": True, "article_ids": []},
            "sections": [],
            "componentes": [
                {"key": "lo_mas_leido", "active": True, "article_ids": list(lo_mas_leido_ids)},
            ],
        }

        fetch_mock = MagicMock(return_value=fetch_fallback_articles or [])

        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved_grid), \
             patch("homev4.views.Article") as mock_art, \
             patch("homev4.views._fetch_component_articles", fetch_mock), \
             patch("homev4.views._block_active", side_effect=lambda _key, val: bool(val)), \
             patch("homev4.views._SUPLEMENTO_SOURCE_BY_WEEKDAY", {}), \
             patch("homev4.views.timezone") as mock_tz:

            mock_art.published = _make_published_mock(available_ids)
            mock_tz.localdate.return_value = datetime.date(2026, 5, 8)
            mock_tz.now.return_value = MagicMock()

            from homev4.views import build_home_data
            result = build_home_data(resolved_grid, publication=None, layout=None)

        comp = next((c for c in result["componentes"] if c["key"] == "lo_mas_leido"), None)
        return comp, fetch_mock

    def test_saved_ids_reads_from_db_by_id(self):
        """When article_ids are saved, articles are fetched from DB by ID — not via _fetch_component_articles."""
        comp, fetch_mock = self._build(lo_mas_leido_ids=[10, 20, 30])
        self.assertIsNotNone(comp)
        self.assertEqual([a.id for a in comp["articles"]], [10, 20, 30])
        fetch_mock.assert_not_called()

    def test_saved_ids_order_preserved(self):
        """The order of articles in the result matches article_ids, not the DB return order."""
        # available_ids is in reversed order; article_ids specifies the canonical order.
        comp, _ = self._build(
            lo_mas_leido_ids=[30, 10, 20],
            available_ids=[10, 20, 30],  # DB would return in this order
        )
        self.assertEqual([a.id for a in comp["articles"]], [30, 10, 20])

    def test_empty_ids_triggers_fallback(self):
        """When article_ids is [], _fetch_component_articles is called as fallback."""
        fallback = [_art(99), _art(98)]
        comp, fetch_mock = self._build(lo_mas_leido_ids=[], fetch_fallback_articles=fallback)
        fetch_mock.assert_called_once_with("lo_mas_leido")
        self.assertEqual([a.id for a in comp["articles"]], [99, 98])

    def test_unpublished_articles_silently_dropped(self):
        """Articles in article_ids that are no longer in Article.published are dropped."""
        comp, _ = self._build(
            lo_mas_leido_ids=[10, 20, 30],
            available_ids=[10, 30],  # 20 is unpublished / deleted
        )
        self.assertEqual([a.id for a in comp["articles"]], [10, 30])

    def test_all_articles_unpublished_returns_empty_list(self):
        """If all saved IDs are unpublished, articles list is empty — no error, no fallback."""
        comp, fetch_mock = self._build(
            lo_mas_leido_ids=[10, 20],
            available_ids=[],  # nothing published
        )
        self.assertEqual(comp["articles"], [])
        fetch_mock.assert_not_called()

    def test_component_key_is_in_result(self):
        """The resulting component entry has key='lo_mas_leido'."""
        comp, _ = self._build(lo_mas_leido_ids=[1, 2])
        self.assertEqual(comp["key"], "lo_mas_leido")
