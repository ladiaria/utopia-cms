"""
Unit tests for the article_search view exclusion logic.

Two-path exclusion mechanism:
  - exclude_ids present in GET (JS sends live DOM state): authoritative, DB lookup skipped.
  - exclude_ids absent: fall back to layout_id DB grid_data exclusion.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.

Core bug this tests: an article removed from the editor DOM (not in exclude_ids) but still
present in the saved DB grid_data must NOT be excluded from search results.
"""
import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from homev4.views import article_search


def _staff_request(params):
    """Build a GET request that passes the staff_member_required decorator."""
    factory = RequestFactory()
    req = factory.get("/homev4/article-search/", params)
    req.user = MagicMock(is_active=True, is_staff=True, is_authenticated=True)
    return req


def _chain_qs(articles=None):
    """Return a queryset mock that supports .filter().exclude().order_by()[:n] chaining."""
    articles = articles or []
    qs = MagicMock()
    qs.filter.return_value = qs
    qs.exclude.return_value = qs
    qs.order_by.return_value = qs
    qs.__getitem__ = MagicMock(return_value=articles)
    return qs


class ArticleSearchTest(SimpleTestCase):

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_query_too_short_returns_empty(self, MockArticle, MockLayout):
        """q shorter than 2 chars → [] without touching DB or Article queryset."""
        req = _staff_request({"q": "a"})
        resp = article_search(req)
        self.assertEqual(json.loads(resp.content), [])
        MockLayout.objects.get.assert_not_called()
        MockArticle.published.filter.assert_not_called()

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_exclude_ids_present_skips_db_lookup(self, MockArticle, MockLayout):
        """When exclude_ids is in the request, HomeLayout DB lookup must not happen."""
        MockArticle.published = _chain_qs()
        req = _staff_request({"q": "python", "exclude_ids": "1,2,3", "layout_id": "99"})
        article_search(req)
        MockLayout.objects.get.assert_not_called()

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_exclude_ids_empty_string_also_skips_db_lookup(self, MockArticle, MockLayout):
        """exclude_ids='' (JS sends empty list when editor is empty) → DB lookup still skipped."""
        MockArticle.published = _chain_qs()
        req = _staff_request({"q": "python", "exclude_ids": "", "layout_id": "99"})
        article_search(req)
        MockLayout.objects.get.assert_not_called()

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_exclude_ids_absent_uses_layout_db(self, MockArticle, MockLayout):
        """When exclude_ids is absent, grid_data is read from DB via layout_id."""
        layout = MagicMock()
        layout.grid_data = {"principal": {"article_ids": [10, 20]}, "sections": [], "componentes": []}
        MockLayout.objects.get.return_value = layout
        MockArticle.published = _chain_qs()

        req = _staff_request({"q": "python", "layout_id": "5"})
        article_search(req)

        MockLayout.objects.get.assert_called_once_with(pk="5")

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_exclude_ids_filters_listed_articles(self, MockArticle, MockLayout):
        """Article IDs in exclude_ids must be passed to qs.exclude(id__in=...)."""
        qs = _chain_qs()
        MockArticle.published = qs

        req = _staff_request({"q": "noticias", "exclude_ids": "7,8,9"})
        article_search(req)

        qs.exclude.assert_called_once_with(id__in={7, 8, 9})

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_removed_article_not_excluded_when_absent_from_exclude_ids(self, MockArticle, MockLayout):
        """
        Core fix: article 42 is in DB grid_data (saved, not yet cleared) but is absent from
        exclude_ids because the user removed it from the editor DOM without saving.
        The view must use exclude_ids as authoritative and not re-exclude article 42.
        """
        layout = MagicMock()
        layout.grid_data = {"principal": {"article_ids": [42]}, "sections": [], "componentes": []}
        MockLayout.objects.get.return_value = layout

        qs = _chain_qs()
        MockArticle.published = qs

        # JS sends current DOM state: article 42 was removed, only 1,2,3 remain.
        req = _staff_request({"q": "noticias", "exclude_ids": "1,2,3", "layout_id": "5"})
        article_search(req)

        MockLayout.objects.get.assert_not_called()
        excluded = qs.exclude.call_args[1]["id__in"]
        self.assertNotIn(42, excluded)
        self.assertEqual(excluded, {1, 2, 3})

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_db_exclusion_covers_all_zones(self, MockArticle, MockLayout):
        """DB fallback must collect IDs from principal, suplemento, especial, sections, and componentes."""
        layout = MagicMock()
        layout.grid_data = {
            "principal": {"article_ids": [1]},
            "suplemento": {"article_ids": [2]},
            "especial": {"article_ids": [3]},
            "sections": [{"slug": "cultura", "article_ids": [4]}],
            "componentes": [{"key": "opinion", "article_ids": [5]}],
        }
        MockLayout.objects.get.return_value = layout
        qs = _chain_qs()
        MockArticle.published = qs

        req = _staff_request({"q": "noticias", "layout_id": "5"})
        article_search(req)

        qs.exclude.assert_called_once_with(id__in={1, 2, 3, 4, 5})

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_no_exclusion_when_no_params(self, MockArticle, MockLayout):
        """Without layout_id and without exclude_ids, qs.exclude() must not be called."""
        qs = _chain_qs()
        MockArticle.published = qs

        req = _staff_request({"q": "noticias"})
        article_search(req)

        qs.exclude.assert_not_called()

    @patch("homev4.views.HomeLayout")
    @patch("homev4.views.Article")
    def test_db_fallback_skips_inactive_blocks(self, MockArticle, MockLayout):
        """
        Inactive blocks must NOT contribute to excluded_ids in the DB fallback path.
        Only articles in blocks with active=True (or active missing, which defaults True)
        should be excluded from search results.
        """
        layout = MagicMock()
        layout.grid_data = {
            "principal":  {"active": True,  "article_ids": [1]},   # active — must be excluded
            "suplemento": {"active": False, "article_ids": [2]},   # inactive — must NOT be excluded
            "especial":   {"active": False, "article_ids": [3]},   # inactive — must NOT be excluded
            "sections":   [
                {"slug": "cultura", "active": True,  "article_ids": [4]},  # active — must be excluded
                {"slug": "deporte", "active": False, "article_ids": [5]},  # inactive — must NOT be excluded
            ],
            "componentes": [
                {"key": "opinion",  "active": True,  "article_ids": [6]},  # active — must be excluded
                {"key": "le_monde", "active": False, "article_ids": [7]},  # inactive — must NOT be excluded
            ],
        }
        MockLayout.objects.get.return_value = layout
        qs = _chain_qs()
        MockArticle.published = qs

        req = _staff_request({"q": "noticias", "layout_id": "5"})
        article_search(req)

        excluded = qs.exclude.call_args[1]["id__in"]
        # Active blocks contribute
        self.assertIn(1, excluded)
        self.assertIn(4, excluded)
        self.assertIn(6, excluded)
        # Inactive blocks must NOT contribute
        self.assertNotIn(2, excluded)
        self.assertNotIn(3, excluded)
        self.assertNotIn(5, excluded)
        self.assertNotIn(7, excluded)
