"""
Unit tests for the Principal block 10-article limit.

Two surfaces under test:

1. resolve_layout_grid_data() — when Principal has no saved_ids, the fallback
   fetches from the edition and truncates to the first 10 articles. Saved IDs
   are not truncated by resolve (save_grid rejects them at write time).

2. save_grid() — rejects POST requests where principal.article_ids has more
   than 10 entries, returning HTTP 400 with an error message.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.
"""
import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from homev4.views import resolve_layout_grid_data, _merge_principal_article_ids


def _art(article_id):
    a = MagicMock()
    a.id = article_id
    return a


def _run_resolve(edition_ids, saved_principal_ids=None):
    """Run resolve_layout_grid_data with a controlled edition and optional saved IDs."""
    grid = {}
    if saved_principal_ids is not None:
        grid["principal"] = {"active": True, "article_ids": list(saved_principal_ids)}

    with patch("homev4.views.get_current_edition") as mock_ed, \
         patch("homev4.views._fetch_source_articles", return_value=[]), \
         patch("homev4.views._fetch_area_articles", return_value=[]), \
         patch("homev4.views._fetch_component_articles", return_value=[]), \
         patch("homev4.views.timezone") as mock_tz:
        mock_ed.return_value.top_articles = [_art(i) for i in edition_ids]
        mock_tz.localdate.return_value = __import__("datetime").date(2026, 5, 8)
        mock_tz.now.return_value = MagicMock()
        return resolve_layout_grid_data(grid)


# ---------------------------------------------------------------------------
# resolve_layout_grid_data — Principal truncation
# ---------------------------------------------------------------------------

class PrincipalFallbackTruncationTest(SimpleTestCase):
    """
    When Principal has no saved article_ids, resolve fetches from the edition
    and must truncate to at most 10 articles.

    Invariants:
    - Edition with > 10 articles → Principal gets exactly the first 10.
    - Edition with exactly 10 → all 10 kept.
    - Edition with < 10 → all articles kept (no padding or error).
    - Edition with 0 articles → Principal stays empty.
    - Truncation preserves original order (first 10, not random).
    - Saved article_ids are NOT truncated by resolve — save_grid owns that.
    """

    def test_edition_with_15_articles_truncated_to_10(self):
        """Edition has 15 articles → Principal gets only the first 10."""
        result = _run_resolve(edition_ids=range(1, 16))
        self.assertEqual(result["principal"]["article_ids"], list(range(1, 11)))

    def test_edition_with_exactly_10_articles_all_kept(self):
        """Edition has exactly 10 → all 10 are kept."""
        result = _run_resolve(edition_ids=range(1, 11))
        self.assertEqual(result["principal"]["article_ids"], list(range(1, 11)))

    def test_edition_with_5_articles_all_kept(self):
        """Edition has fewer than 10 → all are kept, no error."""
        result = _run_resolve(edition_ids=range(1, 6))
        self.assertEqual(result["principal"]["article_ids"], list(range(1, 6)))

    def test_edition_with_0_articles_gives_empty_principal(self):
        """Edition with no articles → Principal is empty, no crash."""
        result = _run_resolve(edition_ids=[])
        self.assertEqual(result["principal"]["article_ids"], [])

    def test_truncation_preserves_order(self):
        """The first 10 articles from the edition are kept in their original order."""
        ids = [50, 30, 10, 40, 20, 60, 70, 80, 90, 100, 110, 120]
        result = _run_resolve(edition_ids=ids)
        self.assertEqual(result["principal"]["article_ids"], ids[:10])

    def test_saved_ids_not_truncated_by_resolve(self):
        """If the editor saved 12 article_ids, resolve leaves them as-is.
        Truncation at save time is enforced by save_grid, not by resolve."""
        saved = list(range(1, 13))  # 12 IDs
        result = _run_resolve(edition_ids=range(1, 20), saved_principal_ids=saved)
        self.assertEqual(result["principal"]["article_ids"], saved)

    def test_saved_ids_used_instead_of_edition(self):
        """When saved_ids exist, the edition is not consulted for Principal."""
        saved = [99, 98, 97]
        result = _run_resolve(edition_ids=range(1, 20), saved_principal_ids=saved)
        # None of the edition IDs (1-19) should appear in Principal
        for eid in range(1, 20):
            self.assertNotIn(eid, result["principal"]["article_ids"])
        self.assertEqual(result["principal"]["article_ids"], saved)

    def test_articles_11_and_beyond_available_for_suplemento(self):
        """Articles beyond position 10 must NOT be in seen_ids, so Suplemento can use them.
        Regression guard: before the fix, article 11 was trapped in Principal's seen_ids."""
        # Edition has IDs 1-15. Suplemento source returns IDs 11, 12, 13.
        # With the fix, 11-15 are NOT in seen_ids, so Suplemento can take them.
        grid = {}
        with patch("homev4.views.get_current_edition") as mock_ed, \
             patch("homev4.views._fetch_source_articles") as mock_fetch_source, \
             patch("homev4.views._fetch_area_articles", return_value=[]), \
             patch("homev4.views._fetch_component_articles", return_value=[]), \
             patch("homev4.views.timezone") as mock_tz:
            mock_ed.return_value.top_articles = [_art(i) for i in range(1, 16)]
            # Suplemento source returns articles 11, 12, 13 (previously trapped in principal)
            mock_fetch_source.return_value = [_art(11), _art(12), _art(13)]
            mock_tz.localdate.return_value = __import__("datetime").date(2026, 5, 7)  # Wednesday
            mock_tz.now.return_value = MagicMock()
            result = resolve_layout_grid_data(grid)
        # Principal must have only 10 articles
        self.assertEqual(len(result["principal"]["article_ids"]), 10)
        # Suplemento must have received articles 11-13 (not blocked by Principal)
        self.assertEqual(result["suplemento"]["article_ids"], [11, 12, 13])


# ---------------------------------------------------------------------------
# save_grid — backend validation
# ---------------------------------------------------------------------------

class SaveGridPrincipalLimitTest(SimpleTestCase):
    """
    Tests for the principal article_ids limit enforced in save_grid().

    Contract:
    - More than 10 IDs in principal → HTTP 400, error message, layout NOT saved.
    - Exactly 10 IDs → accepted (HTTP 200).
    - Fewer than 10 IDs → accepted.
    - Empty principal (fallback state) → accepted.
    - The limit applies regardless of whether the IDs are valid articles.
    """

    def _post(self, principal_ids):
        """POST to save_grid with the given principal article_ids. Returns the response."""
        from homev4.views import save_grid

        factory = RequestFactory()
        body = json.dumps({"grid_data": {"principal": {"active": True, "article_ids": principal_ids}}})
        request = factory.post("/homev4/save-grid/1/", data=body, content_type="application/json")
        request.user = MagicMock()
        request.session = {}

        mock_layout = MagicMock()
        mock_layout.grid_data = {}

        with patch("homev4.views.get_object_or_404", return_value=mock_layout), \
             patch("homev4.views.transaction"), \
             patch("homev4.views._propagate_article_ids"), \
             patch("homev4.views._write_audit_log"), \
             patch("homev4.views._sync_principal_to_edition"), \
             patch("homev4.views._grid_stats", return_value={
                 "principal": len(principal_ids), "suplemento": 0,
                 "sections_active": 0, "sections_total": 0, "componentes_active": [],
             }):
            return save_grid(request, layout_id=1)

    def test_11_principal_ids_returns_400(self):
        """More than 10 IDs → HTTP 400."""
        response = self._post(list(range(1, 12)))
        self.assertEqual(response.status_code, 400)

    def test_11_principal_ids_returns_error_message(self):
        """Error response body contains a meaningful error key."""
        response = self._post(list(range(1, 12)))
        data = json.loads(response.content)
        self.assertIn("error", data)

    def test_24_principal_ids_returns_400(self):
        """24 IDs (the pre-fix production case) → HTTP 400."""
        response = self._post(list(range(1, 25)))
        self.assertEqual(response.status_code, 400)

    def test_10_principal_ids_accepted(self):
        """Exactly 10 IDs → accepted (status 200)."""
        response = self._post(list(range(1, 11)))
        self.assertEqual(response.status_code, 200)

    def test_5_principal_ids_accepted(self):
        """Fewer than 10 IDs → accepted."""
        response = self._post(list(range(1, 6)))
        self.assertEqual(response.status_code, 200)

    def test_empty_principal_ids_accepted(self):
        """Empty list (fallback state, editor didn't pick articles) → accepted."""
        response = self._post([])
        self.assertEqual(response.status_code, 200)

    def test_layout_not_saved_when_limit_exceeded(self):
        """When the limit is exceeded, layout.save must NOT be called."""
        from homev4.views import save_grid

        factory = RequestFactory()
        body = json.dumps({"grid_data": {"principal": {"active": True, "article_ids": list(range(1, 12))}}})
        request = factory.post("/", data=body, content_type="application/json")
        request.user = MagicMock()
        request.session = {}

        mock_layout = MagicMock()
        mock_layout.grid_data = {}

        with patch("homev4.views.get_object_or_404", return_value=mock_layout), \
             patch("homev4.views.transaction"), \
             patch("homev4.views._propagate_article_ids"), \
             patch("homev4.views._write_audit_log"):
            save_grid(request, layout_id=1)

        mock_layout.save.assert_not_called()


# ---------------------------------------------------------------------------
# save_grid — all block limits
# ---------------------------------------------------------------------------

class SaveGridAllBlockLimitsTest(SimpleTestCase):
    """
    Tests for the article_ids limits across all blocks in save_grid().

    Each block has a limit defined in BLOCK_ARTICLE_LIMITS:
      principal: 10, suplemento: 7, especial: 1, area: 2,
      apuntes_del_dia: 1, opinion: 3, recomendadas_lv: 4,
      le_monde: 2, lento: 2.
    """

    def _post(self, grid_data):
        from homev4.views import save_grid

        factory = RequestFactory()
        body = json.dumps({"grid_data": grid_data})
        request = factory.post("/", data=body, content_type="application/json")
        request.user = MagicMock()
        request.session = {}

        mock_layout = MagicMock()
        mock_layout.grid_data = {}

        with patch("homev4.views.get_object_or_404", return_value=mock_layout), \
             patch("homev4.views.transaction"), \
             patch("homev4.views._propagate_article_ids"), \
             patch("homev4.views._write_audit_log"), \
             patch("homev4.views._sync_principal_to_edition"), \
             patch("homev4.views._grid_stats", return_value={
                 "principal": 0, "suplemento": 0,
                 "sections_active": 0, "sections_total": 0, "componentes_active": [],
             }):
            return save_grid(request, layout_id=1)

    def test_especial_over_limit_returns_400(self):
        """especial with 2 IDs (limit 1) → HTTP 400."""
        response = self._post({"especial": {"article_ids": [1, 2]}})
        self.assertEqual(response.status_code, 400)

    def test_especial_at_limit_accepted(self):
        """especial with exactly 1 ID → accepted."""
        response = self._post({"especial": {"article_ids": [1]}})
        self.assertEqual(response.status_code, 200)

    def test_suplemento_over_limit_returns_400(self):
        """suplemento with 8 IDs (limit 7) → HTTP 400."""
        response = self._post({"suplemento": {"article_ids": list(range(1, 9))}})
        self.assertEqual(response.status_code, 400)

    def test_suplemento_at_limit_accepted(self):
        """suplemento with exactly 7 IDs → accepted."""
        response = self._post({"suplemento": {"article_ids": list(range(1, 8))}})
        self.assertEqual(response.status_code, 200)

    def test_area_over_limit_returns_400(self):
        """An area section with 3 IDs (limit 2) → HTTP 400."""
        response = self._post({"sections": [{"slug": "mundo", "article_ids": [1, 2, 3]}]})
        self.assertEqual(response.status_code, 400)

    def test_area_at_limit_accepted(self):
        """An area section with exactly 2 IDs → accepted."""
        response = self._post({"sections": [{"slug": "mundo", "article_ids": [1, 2]}]})
        self.assertEqual(response.status_code, 200)

    def test_opinion_over_limit_returns_400(self):
        """opinion component with 4 IDs (limit 3) → HTTP 400."""
        response = self._post({"componentes": [{"key": "opinion", "article_ids": [1, 2, 3, 4]}]})
        self.assertEqual(response.status_code, 400)

    def test_opinion_at_limit_accepted(self):
        """opinion component with exactly 3 IDs → accepted."""
        response = self._post({"componentes": [{"key": "opinion", "article_ids": [1, 2, 3]}]})
        self.assertEqual(response.status_code, 200)

    def test_recomendadas_lv_over_limit_returns_400(self):
        """recomendadas_lv with 5 IDs (limit 4) → HTTP 400."""
        response = self._post({"componentes": [{"key": "recomendadas_lv", "article_ids": list(range(1, 6))}]})
        self.assertEqual(response.status_code, 400)

    def test_le_monde_over_limit_returns_400(self):
        """le_monde with 3 IDs (limit 2) → HTTP 400."""
        response = self._post({"componentes": [{"key": "le_monde", "article_ids": [1, 2, 3]}]})
        self.assertEqual(response.status_code, 400)

    def test_lento_over_limit_returns_400(self):
        """lento with 3 IDs (limit 2) → HTTP 400."""
        response = self._post({"componentes": [{"key": "lento", "article_ids": [1, 2, 3]}]})
        self.assertEqual(response.status_code, 400)

    def test_apuntes_del_dia_over_limit_returns_400(self):
        """apuntes_del_dia with 2 IDs (limit 1) → HTTP 400."""
        response = self._post({"componentes": [{"key": "apuntes_del_dia", "article_ids": [1, 2]}]})
        self.assertEqual(response.status_code, 400)

    def test_multiple_blocks_valid_accepted(self):
        """All blocks within limits → accepted."""
        response = self._post({
            "principal":  {"article_ids": list(range(1, 11))},
            "suplemento": {"article_ids": list(range(11, 18))},
            "especial":   {"article_ids": [18]},
            "sections":   [{"slug": "mundo", "article_ids": [19, 20]}],
            "componentes": [
                {"key": "opinion",              "article_ids": [20, 21, 22]},
                {"key": "recomendadas_lv",      "article_ids": [23, 24, 25, 26]},
                {"key": "le_monde",             "article_ids": [31, 32]},
                {"key": "lento",                "article_ids": [33, 34]},
                {"key": "apuntes_del_dia",      "article_ids": [35]},
            ],
        })
        self.assertEqual(response.status_code, 200)

    def test_error_message_names_the_offending_block(self):
        """Error response identifies which block exceeded the limit."""
        response = self._post({"componentes": [{"key": "lento", "article_ids": [1, 2, 3]}]})
        data = json.loads(response.content)
        self.assertIn("lento", data.get("error", ""))


class MergePrincipalArticleIdsTest(SimpleTestCase):
    """Unit tests for _merge_principal_article_ids — the function used by the
    refresh task to inject new edition articles into principal."""

    def test_new_article_inserted_at_edition_position(self):
        """A new article from the edition enters at its edition index."""
        current = [10, 20, 30]
        edition = [99, 10, 20, 30]
        result = _merge_principal_article_ids(current, edition)
        self.assertEqual(result[0], 99)
        self.assertIn(10, result)

    def test_existing_articles_keep_their_position(self):
        """Articles already in principal are not moved."""
        current = [10, 20, 30]
        edition = [10, 20, 30]
        result = _merge_principal_article_ids(current, edition)
        self.assertEqual(result, [10, 20, 30])

    def test_result_capped_at_principal_limit(self):
        """When merge would exceed 10 articles the result is truncated to 10."""
        current = list(range(1, 11))        # 10 saved articles
        edition = [99] + list(range(1, 11)) # edition adds article 99 at top
        result = _merge_principal_article_ids(current, edition)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], 99)     # new top article enters
        self.assertNotIn(10, result)        # last saved article is pushed out

    def test_edition_with_24_articles_does_not_inflate_principal(self):
        """Regression: refresh task with 24-article edition must not exceed 10."""
        current = list(range(1, 11))
        edition = list(range(1, 25))        # 24 articles, first 10 already saved
        result = _merge_principal_article_ids(current, edition)
        self.assertEqual(len(result), 10)

    def test_empty_current_ids_fills_up_to_limit(self):
        """With no saved articles, inserts from edition up to the 10-article cap."""
        result = _merge_principal_article_ids([], list(range(1, 25)))
        self.assertEqual(len(result), 10)
        self.assertEqual(result, list(range(1, 11)))

    # --- edition_all_ids: precise removal of home_top=False articles ---

    def test_article_in_todays_edition_home_top_false_is_dropped(self):
        """An article in today's edition with home_top=False (unchecked EN PORTADA)
        is removed from principal on the next celery:refresh run."""
        current = [10, 20, 30]
        edition_top = [10, 30]       # 20 is in today's edition but home_top=False
        edition_all = {10, 20, 30}   # all three are in today's edition
        result = _merge_principal_article_ids(current, edition_top, edition_all_ids=edition_all)
        self.assertNotIn(20, result)
        self.assertIn(10, result)
        self.assertIn(30, result)

    def test_article_from_other_edition_is_kept(self):
        """An article in principal whose ArticleRel belongs to a different edition
        (not today's) is NOT dropped — only today's explicitly-disabled articles are."""
        current = [10, 20, 99]       # 99 is from a different edition
        edition_top = [10, 20]
        edition_all = {10, 20}       # 99 is not in today's edition
        result = _merge_principal_article_ids(current, edition_top, edition_all_ids=edition_all)
        self.assertIn(99, result)    # kept — from another edition
        self.assertIn(10, result)
        self.assertIn(20, result)

    def test_without_edition_all_ids_no_article_is_dropped(self):
        """Without edition_all_ids (backward-compatible call), no article is ever
        dropped — same behaviour as before the bidirectional sync."""
        current = [10, 20, 30]
        edition_top = [10, 30]       # 20 not in edition but no edition_all_ids given
        result = _merge_principal_article_ids(current, edition_top)
        self.assertIn(20, result)    # kept — no information to decide otherwise

    def test_editor_order_preserved_after_removal(self):
        """The remaining articles keep their editor-set order after a dropped article."""
        current = [10, 20, 30, 40]
        edition_top = [10, 30, 40]
        edition_all = {10, 20, 30, 40}   # 20 in today's edition, home_top=False
        result = _merge_principal_article_ids(current, edition_top, edition_all_ids=edition_all)
        self.assertEqual(result, [10, 30, 40])

