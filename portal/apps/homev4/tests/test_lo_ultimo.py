"""
Unit tests for the lo_ultimo block dynamic behaviour in _fetch_component_articles().

The block always shows 3 articles. Pinned articles stay at their saved position
as long as they are published and not claimed by a higher-priority block. Every
non-pinned slot is filled with the most recently published article available.

Scenarios under test:
  1. No saved_ids → return the 3 most recent articles directly.
  2. 3 non-pinned articles, new article published → new article enters, oldest
     leaves (all slots filled dynamically by recency).
  3. 1 pinned + 2 non-pinned → pinned stays at its saved position; the 2 other
     slots are filled with the 2 most recent non-pinned articles.
  4. All 3 pinned → all 3 stay in saved order; no dynamic fetch needed.
  5. 2 pinned + 1 non-pinned → 2 pinned stay; 1 dynamic fills the free slot.
  6. Pinned article no longer published → treated as non-pinned (evicted); slot
     filled dynamically.
  7. Pinned article in exclude_ids (claimed by higher-priority block) → evicted;
     slot filled dynamically.
  8. 3 non-pinned, no new articles → saved articles replaced by 3 most recent
     (which happen to be the same 3).
  9. saved_ids has fewer than 3 entries → leftover dynamic articles fill remaining
     slots up to 3.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


def _art(article_id):
    a = MagicMock()
    a.id = article_id
    return a


class FakeQS:
    """
    Minimal queryset mock supporting the call chain used by _fetch_component_articles
    for lo_ultimo:

      Article.published
        .filter(id__in=...)          → for pinned lookup
        .select_related(...)         → no-op, returns self
        .order_by("-date_published") → no-op, order is defined by _ordered
        .exclude(id__in=...)         → filters out given IDs
        [:n]                         → slice
    """

    def __init__(self, ordered, available_ids=None):
        # ordered: articles in the order they should be returned (most recent first)
        self._ordered = list(ordered)
        # available_ids: set of IDs that exist in Article.published (for filter)
        self._available = {a.id: a for a in self._ordered} if available_ids is None else available_ids

    def filter(self, **kwargs):
        id__in = set(kwargs.get("id__in", []))
        filtered = [a for a in self._ordered if a.id in id__in]
        return FakeQS(filtered, self._available)

    def select_related(self, *args):
        return self

    def order_by(self, *args):
        return self

    def exclude(self, **kwargs):
        id__in = set(kwargs.get("id__in", []))
        filtered = [a for a in self._ordered if a.id not in id__in]
        return FakeQS(filtered, self._available)

    def __getitem__(self, key):
        return self._ordered[key]

    def __iter__(self):
        return iter(self._ordered)


def _run(saved_ids, pinned_ids=None, exclude_ids=None, published_ordered=None):
    """
    Call _fetch_component_articles("lo_ultimo", ...) with a controlled
    Article.published queryset.

    published_ordered: articles in recency order (most recent first).
                       Defaults to empty list.
    """
    published_ordered = published_ordered or []
    fake_qs = FakeQS(published_ordered)

    with patch("homev4.views.Article") as mock_art:
        mock_art.published = fake_qs
        from homev4.views import _fetch_component_articles
        return _fetch_component_articles(
            "lo_ultimo",
            saved_ids=saved_ids,
            pinned_ids=set(pinned_ids or []),
            exclude_ids=set(exclude_ids or []),
        )


def _ids(articles):
    return [a.id for a in articles]


class LoUltimoNoSavedIdsTest(SimpleTestCase):
    """When saved_ids is None or empty, return the 3 most recent articles directly."""

    def test_no_saved_ids_returns_3_most_recent(self):
        """No saved order yet → 3 most recent returned in recency order."""
        arts = [_art(10), _art(9), _art(8), _art(7)]
        result = _run(saved_ids=None, published_ordered=arts)
        self.assertEqual(_ids(result), [10, 9, 8])

    def test_no_saved_ids_fewer_than_3_published(self):
        """Fewer than 3 articles published → return all of them."""
        arts = [_art(5), _art(4)]
        result = _run(saved_ids=None, published_ordered=arts)
        self.assertEqual(_ids(result), [5, 4])

    def test_no_saved_ids_empty_published(self):
        """No published articles → return empty list."""
        result = _run(saved_ids=None, published_ordered=[])
        self.assertEqual(result, [])


class LoUltimoNoPinnedTest(SimpleTestCase):
    """All slots are dynamic when nothing is pinned."""

    def test_new_article_replaces_oldest(self):
        """New article published (ID 4, most recent) enters; oldest (ID 1) is dropped."""
        # saved: [1, 2, 3] — none pinned
        # published order: 4 (new), 3, 2, 1
        arts = [_art(4), _art(3), _art(2), _art(1)]
        result = _run(saved_ids=[1, 2, 3], published_ordered=arts)
        self.assertEqual(_ids(result), [4, 3, 2])

    def test_no_new_articles_same_3_returned(self):
        """No new articles → the same 3 come back (still the most recent)."""
        arts = [_art(3), _art(2), _art(1)]
        result = _run(saved_ids=[1, 2, 3], published_ordered=arts)
        self.assertEqual(_ids(result), [3, 2, 1])

    def test_multiple_new_articles_oldest_two_dropped(self):
        """Two new articles published → two oldest saved articles are dropped."""
        arts = [_art(5), _art(4), _art(3), _art(2), _art(1)]
        result = _run(saved_ids=[1, 2, 3], published_ordered=arts)
        self.assertEqual(_ids(result), [5, 4, 3])

    def test_exclude_ids_not_in_result(self):
        """Articles in exclude_ids are not used as dynamic fill."""
        # exclude 4 and 5; next available are 3, 2, 1
        arts = [_art(5), _art(4), _art(3), _art(2), _art(1)]
        result = _run(saved_ids=[1, 2, 3], exclude_ids={4, 5}, published_ordered=arts)
        self.assertEqual(_ids(result), [3, 2, 1])


class LoUltimoPinnedTest(SimpleTestCase):
    """Pinned articles hold their saved position; free slots are filled dynamically."""

    def test_one_pinned_two_dynamic(self):
        """1 pinned at position 0; positions 1-2 filled with 2 most recent non-pinned."""
        # saved: [10, 2, 3] — 10 is pinned
        # published order (most recent first): 10, 5, 4, 3, 2, 1
        arts = [_art(10), _art(5), _art(4), _art(3), _art(2), _art(1)]
        result = _run(saved_ids=[10, 2, 3], pinned_ids={10}, published_ordered=arts)
        # slot 0 → pinned 10; slots 1-2 → 2 most recent excluding 10 = 5, 4
        self.assertEqual(_ids(result), [10, 5, 4])

    def test_all_3_pinned_stay_in_saved_order(self):
        """All 3 pinned → returned in saved order, no dynamic fill."""
        arts = [_art(30), _art(20), _art(10)]
        result = _run(saved_ids=[10, 20, 30], pinned_ids={10, 20, 30}, published_ordered=arts)
        self.assertEqual(_ids(result), [10, 20, 30])

    def test_two_pinned_one_dynamic(self):
        """2 pinned keep their positions; 1 slot filled dynamically."""
        arts = [_art(99), _art(20), _art(10), _art(5)]
        result = _run(saved_ids=[10, 20, 3], pinned_ids={10, 20}, published_ordered=arts)
        # slot 0 → pinned 10; slot 1 → pinned 20; slot 2 → most recent non-pinned = 99
        self.assertEqual(_ids(result), [10, 20, 99])

    def test_pinned_not_in_published_is_evicted(self):
        """Pinned article no longer published → treated as non-pinned; slot filled dynamically."""
        # 10 was pinned but is now unpublished (not in published_ordered)
        arts = [_art(5), _art(4), _art(3)]
        result = _run(saved_ids=[10, 2, 3], pinned_ids={10}, published_ordered=arts)
        # 10 not in published → valid_pinned empty → all 3 slots dynamic
        self.assertEqual(_ids(result), [5, 4, 3])

    def test_pinned_in_exclude_ids_is_evicted(self):
        """Pinned article claimed by a higher-priority block → evicted; slot filled dynamically."""
        arts = [_art(10), _art(5), _art(4), _art(3)]
        result = _run(saved_ids=[10, 2, 3], pinned_ids={10}, exclude_ids={10}, published_ordered=arts)
        # 10 is in exclude_ids → not a valid_pinned candidate → all slots dynamic
        # dynamic excludes {10} → [5, 4, 3]
        self.assertEqual(_ids(result), [5, 4, 3])

    def test_pinned_position_preserved_regardless_of_recency(self):
        """Pinned article at position 2 (last) stays last even if newer articles exist."""
        arts = [_art(99), _art(50), _art(1)]
        # 1 is pinned at position 2 (oldest but fixed)
        result = _run(saved_ids=[10, 20, 1], pinned_ids={1}, published_ordered=arts)
        # slots 0-1 → dynamic (99, 50); slot 2 → pinned 1
        self.assertEqual(_ids(result), [99, 50, 1])


class LoUltimoEdgeCasesTest(SimpleTestCase):
    """Edge cases: fewer saved slots, all articles excluded, etc."""

    def test_saved_ids_fewer_than_3_fills_remaining_from_dynamic(self):
        """saved_ids has only 1 entry → remaining 2 slots filled with next dynamic articles."""
        arts = [_art(5), _art(4), _art(3)]
        result = _run(saved_ids=[5], published_ordered=arts)
        # slot 0 → dynamic 5; leftover: 4, 3
        self.assertEqual(_ids(result), [5, 4, 3])

    def test_all_dynamic_excluded_returns_empty(self):
        """All published articles in exclude_ids → nothing to fill, result is empty."""
        arts = [_art(1), _art(2), _art(3)]
        result = _run(saved_ids=[1, 2, 3], exclude_ids={1, 2, 3}, published_ordered=arts)
        self.assertEqual(result, [])

    def test_result_never_exceeds_3(self):
        """Result is always capped at 3 regardless of how many are published."""
        arts = [_art(i) for i in range(10, 0, -1)]  # 10 articles
        result = _run(saved_ids=None, published_ordered=arts)
        self.assertLessEqual(len(result), 3)
