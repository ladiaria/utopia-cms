"""
Tests for N+1 lazy-load prevention in build_home_data and _fetch_component_articles.

2026-05-20 optimization:
  _ARTICLE_AUTH_SELECT_RELATED = ("main_section__edition__publication", "main_section__section")
  _ARTICLE_PREFETCH_RELATED    = ("photo__extended__photographer", "byline")

Every article fetch must call:
  .select_related(*_ARTICLE_AUTH_SELECT_RELATED)
  .prefetch_related(*_ARTICLE_PREFETCH_RELATED)

so that templates accessing article.photo, article.byline, and
article.main_section.section don't trigger per-article DB hits.

apuntes_del_dia is a special case: Section.latest() returns a RawQuerySet that
doesn't support select_related/prefetch_related. The function re-fetches the
returned articles by ID through Article.published with the full chain.

Scenarios covered:
  1. Constants hold both expected chains.
  2-3.   _fetch_suplemento_articles: prefetch called on saved-IDs path.
  4-5.   _fetch_area_articles: prefetch called on saved-IDs path.
  6-7.   _fetch_component_articles humor/recomendadas/le_monde/opinion: prefetch on saved-IDs.
  8-11.  apuntes_del_dia: re-fetch by ID, empty latest, unpublished dropped, DoesNotExist.
  12-13. lo_ultimo dynamic queryset has prefetch applied; soft-pin path too.
  14-15. build_home_data principal block: select+prefetch called.
  16-17. build_home_data sections block: select+prefetch called.
  18.    build_home_data lo_mas_leido component (saved-IDs): prefetch called.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.
"""
import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _art(article_id):
    a = MagicMock()
    a.id = article_id
    return a


class TrackingFakeQS:
    """
    Queryset mock that records select_related and prefetch_related calls.
    All derived querysets (returned by filter/exclude/order_by) share the
    same log list, so callers can inspect calls made at any point in the chain.
    """

    def __init__(self, articles, _log=None):
        self._articles = list(articles)
        self._log = _log if _log is not None else []

    def _child(self, articles):
        return TrackingFakeQS(articles, self._log)

    def filter(self, **kwargs):
        id__in = set(kwargs.get("id__in", []))
        return self._child([a for a in self._articles if a.id in id__in])

    def select_related(self, *args):
        self._log.append(("select_related", args))
        return self

    def prefetch_related(self, *args):
        self._log.append(("prefetch_related", args))
        return self

    def order_by(self, *args):
        return self

    def exclude(self, **kwargs):
        result = list(self._articles)
        for key, val in kwargs.items():
            val_set = set(val)
            if key == "id__in":
                result = [a for a in result if a.id not in val_set]
        return self._child(result)

    def __iter__(self):
        return iter(self._articles)

    def __getitem__(self, key):
        return self._articles[key]

    # Assertion helpers
    def prefetch_was_called_with(self, *args):
        # Subset check: true if any prefetch_related call included all given args.
        # Extra args (e.g. Prefetch objects added by callers) are allowed.
        for call_name, call_args in self._log:
            if call_name == "prefetch_related" and all(a in call_args for a in args):
                return True
        return False

    def select_was_called_with(self, *args):
        return ("select_related", args) in self._log

    @property
    def log(self):
        return self._log


def _make_qs(articles):
    """Return a TrackingFakeQS pre-loaded with the given articles."""
    return TrackingFakeQS(articles)


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

class ConstantsTest(SimpleTestCase):
    """_ARTICLE_AUTH_SELECT_RELATED and _ARTICLE_PREFETCH_RELATED have correct values."""

    def test_select_related_contains_publication_chain(self):
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        self.assertIn("main_section__edition__publication", _ARTICLE_AUTH_SELECT_RELATED)

    def test_select_related_contains_section_chain(self):
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        self.assertIn("main_section__section", _ARTICLE_AUTH_SELECT_RELATED)

    def test_select_related_is_tuple_or_list(self):
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        self.assertIsInstance(_ARTICLE_AUTH_SELECT_RELATED, (tuple, list))

    def test_prefetch_contains_photo_chain(self):
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        self.assertIn("photo__extended__photographer", _ARTICLE_PREFETCH_RELATED)

    def test_prefetch_contains_byline(self):
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        self.assertIn("byline", _ARTICLE_PREFETCH_RELATED)

    def test_prefetch_is_tuple_or_list(self):
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        self.assertIsInstance(_ARTICLE_PREFETCH_RELATED, (tuple, list))


# ---------------------------------------------------------------------------
# 2-3. _fetch_suplemento_articles
# ---------------------------------------------------------------------------

class FetchSupplementoArticlesPrefetchTest(SimpleTestCase):
    """_fetch_suplemento_articles fetches with select_related + prefetch_related."""

    def _run(self, saved_ids, published):
        qs = _make_qs(published)
        with patch("homev4.views.Article") as mock_art:
            mock_art.published = qs
            from homev4.views import _fetch_suplemento_articles
            result = _fetch_suplemento_articles({"article_ids": saved_ids})
        return result, qs

    def test_prefetch_called_with_photo_and_byline(self):
        articles = [_art(1), _art(2)]
        _, qs = self._run([1, 2], articles)
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))

    def test_select_related_called_with_both_chains(self):
        articles = [_art(1), _art(2)]
        _, qs = self._run([1, 2], articles)
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        self.assertTrue(qs.select_was_called_with(*_ARTICLE_AUTH_SELECT_RELATED))

    def test_empty_saved_ids_returns_empty_no_query(self):
        qs = _make_qs([])
        with patch("homev4.views.Article") as mock_art:
            mock_art.published = qs
            from homev4.views import _fetch_suplemento_articles
            result = _fetch_suplemento_articles({"article_ids": []})
        self.assertEqual(result, [])
        self.assertEqual(qs.log, [])  # no DB query issued

    def test_order_follows_saved_ids_not_db_order(self):
        arts = [_art(1), _art(2), _art(3)]
        result, _ = self._run([3, 1, 2], arts)
        self.assertEqual([a.id for a in result], [3, 1, 2])

    def test_unpublished_article_silently_dropped(self):
        arts = [_art(1), _art(3)]  # 2 is not in published
        result, _ = self._run([1, 2, 3], arts)
        self.assertEqual([a.id for a in result], [1, 3])


# ---------------------------------------------------------------------------
# 4-5. _fetch_area_articles (saved-IDs path)
# ---------------------------------------------------------------------------

class FetchAreaArticlesPrefetchTest(SimpleTestCase):
    """_fetch_area_articles(saved_ids=[...]) fetches with select+prefetch."""

    def _run(self, saved_ids, published):
        qs = _make_qs(published)
        with patch("homev4.views.Article") as mock_art:
            mock_art.published = qs
            from homev4.views import _fetch_area_articles
            result = _fetch_area_articles("section", "deportes", saved_ids)
        return result, qs

    def test_prefetch_called(self):
        _, qs = self._run([10, 20], [_art(10), _art(20)])
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))

    def test_select_related_called(self):
        _, qs = self._run([10], [_art(10)])
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        self.assertTrue(qs.select_was_called_with(*_ARTICLE_AUTH_SELECT_RELATED))

    def test_empty_saved_ids_uses_fallback_not_filter(self):
        # When saved_ids is empty, _fetch_source_articles is called instead.
        qs = _make_qs([])
        with patch("homev4.views.Article") as mock_art, \
             patch("homev4.views._fetch_source_articles", return_value=[]) as mock_src:
            mock_art.published = qs
            from homev4.views import _fetch_area_articles
            _fetch_area_articles("section", "deportes", [])
        mock_src.assert_called_once()
        self.assertEqual(qs.log, [])  # no direct DB query


# ---------------------------------------------------------------------------
# 6-7. _fetch_component_articles — saved-IDs paths
# ---------------------------------------------------------------------------

class ComponentArticlesSavedIdsPrefetchTest(SimpleTestCase):
    """
    Components that use the saved-IDs path (humor, recomendadas, le_monde,
    lento, opinion) all call select_related + prefetch_related.
    """

    def _run(self, key, saved_ids, published):
        qs = _make_qs(published)
        with patch("homev4.views.Article") as mock_art:
            mock_art.published = qs
            from homev4.views import _fetch_component_articles
            result = _fetch_component_articles(key, saved_ids=saved_ids)
        return result, qs

    def _assert_both_optimizations(self, qs):
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED, _ARTICLE_PREFETCH_RELATED
        self.assertTrue(qs.select_was_called_with(*_ARTICLE_AUTH_SELECT_RELATED),
                        "select_related not called with the right chains")
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED),
                        "prefetch_related not called with photo/byline")

    def test_humor_saved_ids_has_prefetch(self):
        _, qs = self._run("humor", [1, 2], [_art(1), _art(2)])
        self._assert_both_optimizations(qs)

    def test_recomendadas_lv_saved_ids_has_prefetch(self):
        _, qs = self._run("recomendadas_lv", [5], [_art(5)])
        self._assert_both_optimizations(qs)

    def test_le_monde_saved_ids_has_prefetch(self):
        _, qs = self._run("le_monde", [3], [_art(3)])
        self._assert_both_optimizations(qs)

    def test_lento_saved_ids_has_prefetch(self):
        _, qs = self._run("lento", [4], [_art(4)])
        self._assert_both_optimizations(qs)

    def test_opinion_saved_ids_has_prefetch(self):
        _, qs = self._run("opinion", [9], [_art(9)])
        self._assert_both_optimizations(qs)

    def test_humor_no_saved_ids_no_direct_db_query(self):
        # When saved_ids is empty, humor falls back to section.latest() — no filter() call.
        qs = _make_qs([])
        with patch("homev4.views.Article") as mock_art, \
             patch("homev4.views.Section") as mock_sec:
            mock_art.published = qs
            mock_sec.objects.get.return_value.latest.return_value = []
            from homev4.views import _fetch_component_articles
            _fetch_component_articles("humor", saved_ids=[])
        self.assertEqual(qs.log, [])  # no direct Article.published query

    def test_recomendadas_no_saved_ids_returns_empty(self):
        result, _ = self._run("recomendadas_lv", [], [])
        self.assertEqual(result, [])

    def test_saved_order_preserved(self):
        result, _ = self._run("humor", [3, 1, 2], [_art(1), _art(2), _art(3)])
        self.assertEqual([a.id for a in result], [3, 1, 2])


# ---------------------------------------------------------------------------
# 8-11. _fetch_component_articles("apuntes_del_dia")
# ---------------------------------------------------------------------------

class ApuntesDelDiaPrefetchTest(SimpleTestCase):
    """
    apuntes_del_dia re-fetches articles returned by section.latest() through
    Article.published so select_related and prefetch_related can be applied.
    """

    def _run(self, raw_articles, available_ids=None):
        """
        raw_articles: articles returned by section.latest() (RawQuerySet substitute).
        available_ids: IDs present in Article.published (defaults to all raw IDs).
        """
        if available_ids is None:
            available_ids = [a.id for a in raw_articles]
        published_arts = [_art(i) for i in available_ids]
        qs = _make_qs(published_arts)

        section_mock = MagicMock()
        section_mock.latest.return_value = raw_articles

        with patch("homev4.views.Article") as mock_art, \
             patch("homev4.views.Section") as mock_sec:
            mock_art.published = qs
            mock_sec.objects.get.return_value = section_mock
            from homev4.views import _fetch_component_articles
            result = _fetch_component_articles("apuntes_del_dia")

        return result, qs

    def test_refetches_via_article_published(self):
        """When latest() returns 1 article, Article.published.filter is called with its ID."""
        raw = [_art(42)]
        result, qs = self._run(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 42)

    def test_select_related_called_with_both_chains(self):
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        _, qs = self._run([_art(10)])
        self.assertTrue(qs.select_was_called_with(*_ARTICLE_AUTH_SELECT_RELATED))

    def test_prefetch_called_with_photo_and_byline(self):
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        _, qs = self._run([_art(10)])
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))

    def test_empty_latest_returns_empty_no_db_query(self):
        """When latest() returns no articles, no Article.published query is issued."""
        qs = _make_qs([])
        section_mock = MagicMock()
        section_mock.latest.return_value = []

        with patch("homev4.views.Article") as mock_art, \
             patch("homev4.views.Section") as mock_sec:
            mock_art.published = qs
            mock_sec.objects.get.return_value = section_mock
            from homev4.views import _fetch_component_articles
            result = _fetch_component_articles("apuntes_del_dia")

        self.assertEqual(result, [])
        self.assertEqual(qs.log, [])  # no DB query

    def test_unpublished_article_dropped_after_refetch(self):
        """Article returned by latest() that is no longer in Article.published is dropped."""
        raw = [_art(99)]
        result, _ = self._run(raw, available_ids=[])  # 99 not in published
        self.assertEqual(result, [])

    def test_section_does_not_exist_returns_empty(self):
        """When the section slug is not found, return empty list without error."""
        from django.core.exceptions import ObjectDoesNotExist
        qs = _make_qs([])
        with patch("homev4.views.Article") as mock_art, \
             patch("homev4.views.Section") as mock_sec:
            mock_art.published = qs
            mock_sec.objects.get.side_effect = mock_sec.DoesNotExist
            from homev4.views import _fetch_component_articles
            result = _fetch_component_articles("apuntes_del_dia")
        self.assertEqual(result, [])

    @override_settings(HOMEV4_APUNTES_SECTION_SLUG="custom-apuntes")
    def test_uses_configured_section_slug(self):
        """The slug used to look up the section comes from settings."""
        section_mock = MagicMock()
        section_mock.latest.return_value = []
        qs = _make_qs([])

        with patch("homev4.views.Article") as mock_art, \
             patch("homev4.views.Section") as mock_sec:
            mock_art.published = qs
            mock_sec.objects.get.return_value = section_mock
            from homev4.views import _fetch_component_articles
            _fetch_component_articles("apuntes_del_dia")

        mock_sec.objects.get.assert_called_once_with(slug="custom-apuntes")


# ---------------------------------------------------------------------------
# 12-13. lo_ultimo dynamic and soft-pin paths
# ---------------------------------------------------------------------------

class LoUltimoPrefetchTest(SimpleTestCase):
    """
    _fetch_component_articles("lo_ultimo") must apply prefetch_related on both
    the anchored-article fetch and the dynamic queryset.
    """

    def _run(self, saved_ids, published, pinned_ids=None, exclude_ids=None,
             soft_pin_saved=False):
        qs = _make_qs(published)
        with patch("homev4.views.Article") as mock_art, \
             patch("homev4.views.settings") as mock_settings:
            mock_art.published = qs
            # Disable source exclusions so the fake queryset isn't filtered unexpectedly.
            mock_settings.HOMEV4_LO_ULTIMO_EXCLUDE_SECTION_SLUGS = []
            mock_settings.HOMEV4_LO_ULTIMO_EXCLUDE_CATEGORY_SLUGS = []
            mock_settings.HOMEV4_LO_ULTIMO_EXCLUDE_PUBLICATION_SLUGS = []
            from homev4.views import _fetch_component_articles
            result = _fetch_component_articles(
                "lo_ultimo",
                saved_ids=saved_ids,
                pinned_ids=set(pinned_ids or []),
                exclude_ids=set(exclude_ids or []),
                soft_pin_saved=soft_pin_saved,
            )
        return result, qs

    def test_dynamic_query_has_prefetch(self):
        """When there are open slots, the dynamic Article.published query uses prefetch_related."""
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        arts = [_art(1), _art(2), _art(3)]
        _, qs = self._run(saved_ids=None, published=arts)
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))

    def test_dynamic_query_has_select_related(self):
        """The dynamic queryset also applies select_related with the full chain."""
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        arts = [_art(1), _art(2), _art(3)]
        _, qs = self._run(saved_ids=None, published=arts)
        self.assertTrue(qs.select_was_called_with(*_ARTICLE_AUTH_SELECT_RELATED))

    def test_soft_pin_anchor_fetch_has_prefetch(self):
        """In soft-pin mode, the anchored-article lookup also has prefetch_related."""
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        arts = [_art(10), _art(11), _art(12)]
        _, qs = self._run(
            saved_ids=[10, 11, 12],
            published=arts,
            soft_pin_saved=True,
        )
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))

    def test_pinned_anchor_fetch_has_prefetch(self):
        """In pinned mode, the anchored-article lookup also has prefetch_related."""
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        arts = [_art(5), _art(6), _art(7)]
        _, qs = self._run(
            saved_ids=[5, 6, 7],
            published=arts,
            pinned_ids={5},
            soft_pin_saved=False,
        )
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))


# ---------------------------------------------------------------------------
# 14-18. build_home_data — principal, sections, lo_mas_leido
# ---------------------------------------------------------------------------

def _minimal_resolved_grid(principal_ids=None, suplemento_ids=None,
                            section_ids=None, component_key=None, component_ids=None):
    """
    Return a resolved grid dict that exercises only the specified blocks.
    """
    grid = {
        "principal":  {"active": True, "article_ids": list(principal_ids or [])},
        "suplemento": {"active": bool(suplemento_ids), "article_ids": list(suplemento_ids or [])},
        "especial":   {"active": False, "article_ids": []},
        "sections": [],
        "componentes": [],
    }
    if section_ids is not None:
        grid["sections"] = [
            {"type": "section", "slug": "test-section", "name": "Test",
             "active": True, "article_ids": list(section_ids)}
        ]
    if component_key and component_ids is not None:
        grid["componentes"] = [
            {"key": component_key, "active": True, "article_ids": list(component_ids)}
        ]
    return grid


def _run_build(resolved_grid, published_articles):
    """
    Run build_home_data with a controlled resolved grid and article set.
    Returns (result_dict, TrackingFakeQS).
    """
    qs = _make_qs(published_articles)

    with patch("homev4.views.resolve_layout_grid_data", return_value=resolved_grid), \
         patch("homev4.views.Article") as mock_art, \
         patch("homev4.views._block_active", side_effect=lambda _k, v: bool(v)), \
         patch("homev4.views._SUPLEMENTO_SOURCE_BY_WEEKDAY", {}), \
         patch("homev4.views.timezone") as mock_tz, \
         patch("homev4.views._resolve_section_template", return_value=""), \
         patch("homev4.views._resolve_sidebar_template", return_value=""), \
         patch("homev4.views._fetch_component_articles", return_value=[]), \
         patch("homev4.views._resolve_newsletter_refs", return_value=[]):

        mock_art.published = qs
        mock_tz.localdate.return_value = datetime.date(2026, 5, 20)
        mock_tz.now.return_value = MagicMock()

        from homev4.views import build_home_data
        result = build_home_data(resolved_grid, publication=None, layout=None)

    return result, qs


class BuildHomeDataPrincipalPrefetchTest(SimpleTestCase):
    """build_home_data principal block applies select_related + prefetch_related."""

    def _build_with_principal(self, ids):
        arts = [_art(i) for i in ids]
        grid = _minimal_resolved_grid(principal_ids=ids)
        return _run_build(grid, arts)

    def test_prefetch_called_for_principal(self):
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        _, qs = self._build_with_principal([1, 2, 3])
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))

    def test_select_related_called_for_principal(self):
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        _, qs = self._build_with_principal([1, 2])
        self.assertTrue(qs.select_was_called_with(*_ARTICLE_AUTH_SELECT_RELATED))

    def test_articles_returned_in_saved_order(self):
        result, _ = self._build_with_principal([3, 1, 2])
        ids = [a.id for a in result["principal_articles"]]
        self.assertEqual(ids, [3, 1, 2])

    def test_unpublished_article_dropped(self):
        arts = [_art(1), _art(3)]  # 2 is missing from published
        grid = _minimal_resolved_grid(principal_ids=[1, 2, 3])
        result, _ = _run_build(grid, arts)
        ids = [a.id for a in result["principal_articles"]]
        self.assertNotIn(2, ids)
        self.assertEqual(ids, [1, 3])

    def test_empty_principal_ids_no_query(self):
        grid = _minimal_resolved_grid(principal_ids=[])
        _, qs = _run_build(grid, [])
        self.assertEqual(qs.log, [])


class BuildHomeDataSectionsPrefetchTest(SimpleTestCase):
    """build_home_data sections block applies select_related + prefetch_related."""

    def _build_with_section(self, ids):
        arts = [_art(i) for i in ids]
        grid = _minimal_resolved_grid(section_ids=ids)
        return _run_build(grid, arts)

    def test_prefetch_called_for_sections(self):
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        _, qs = self._build_with_section([10, 11])
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))

    def test_select_related_called_for_sections(self):
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        _, qs = self._build_with_section([10])
        self.assertTrue(qs.select_was_called_with(*_ARTICLE_AUTH_SELECT_RELATED))

    def test_section_articles_in_result(self):
        result, _ = self._build_with_section([20, 21])
        sections = result["sections"]
        self.assertEqual(len(sections), 1)
        ids = [a.id for a in sections[0]["articles"]]
        self.assertEqual(ids, [20, 21])

    def test_empty_section_ids_no_query(self):
        grid = _minimal_resolved_grid(section_ids=[])
        _, qs = _run_build(grid, [])
        self.assertEqual(qs.log, [])


class BuildHomeDataLoMasLeidoPrefetchTest(SimpleTestCase):
    """build_home_data lo_mas_leido component (saved-IDs path) uses select+prefetch."""

    def _build_with_lo_mas_leido(self, ids):
        arts = [_art(i) for i in ids]
        grid = _minimal_resolved_grid(component_key="lo_mas_leido", component_ids=ids)
        return _run_build(grid, arts)

    def test_prefetch_called_for_lo_mas_leido(self):
        from homev4.views import _ARTICLE_PREFETCH_RELATED
        _, qs = self._build_with_lo_mas_leido([50, 51, 52])
        self.assertTrue(qs.prefetch_was_called_with(*_ARTICLE_PREFETCH_RELATED))

    def test_select_related_called_for_lo_mas_leido(self):
        from homev4.views import _ARTICLE_AUTH_SELECT_RELATED
        _, qs = self._build_with_lo_mas_leido([50])
        self.assertTrue(qs.select_was_called_with(*_ARTICLE_AUTH_SELECT_RELATED))

    def test_order_follows_component_ids(self):
        result, _ = self._build_with_lo_mas_leido([53, 51, 52])
        comp = next(c for c in result["componentes"] if c["key"] == "lo_mas_leido")
        self.assertEqual([a.id for a in comp["articles"]], [53, 51, 52])
