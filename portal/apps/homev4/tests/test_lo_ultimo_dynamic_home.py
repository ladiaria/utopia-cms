"""
TDD tests for the dynamic refresh of the "Lo último" block on the LIVE home.

Reported bug
------------
On the live home the block stays frozen: new articles only show up after an editor
opens the layout editor and clicks "Últimos disponibles". The block is supposed to
refresh its non-pinned slots automatically on every request, keeping only the
explicitly pinned articles fixed.

Root cause
----------
build_home_data() fetches lo_ultimo with soft_pin_saved=True. In that mode
_fetch_component_articles() anchors EVERY saved article (not only the pinned ones),
so dynamic_slots == 0 and no fresh article is ever pulled in. The block therefore
shows whatever was last persisted in grid_data until a slot is evicted (article
unpublished or claimed by a higher-priority block) or the editor button rewrites it.

Intended behaviour (the fix)
----------------------------
The live render must request lo_ultimo with soft_pin_saved=False so that:
  - explicitly pinned articles keep their saved position, and
  - every non-pinned slot is filled with the most recently published article.

These tests are written BEFORE the fix and are expected to FAIL until build_home_data
stops soft-pinning saved articles on the live render path. The companion unit tests in
test_lo_ultimo.py already cover _fetch_component_articles() in its (correct) default
mode — the gap exercised here is specifically the build_home_data call site.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.
"""
import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from homev4.views import build_home_data, build_editor_data
# Reuse the queryset double already used by the lo_ultimo unit tests so the real
# _fetch_component_articles() can run end-to-end inside build_home_data().
from homev4.tests.test_lo_ultimo import FakeQS


# A fixed "now" so build_home_data's minutes_ago computation is deterministic.
_NOW = datetime.datetime(2026, 4, 19, 12, 0, 0)
# A known Sunday: weekday()=6 → no suplemento source, keeps the sections path inert.
_SUNDAY = datetime.date(2026, 4, 19)


def _art(article_id, minutes_old=5):
    """Mock Article with an id and a real date_published (so minutes_ago works)."""
    a = MagicMock()
    a.id = article_id
    a.date_published = _NOW - datetime.timedelta(minutes=minutes_old)
    return a


def _empty_static_resolved(lo_ultimo_comp):
    """A resolved grid with no static content — only the lo_ultimo component.

    Keeping principal/suplemento/especial/sections empty means the bulk fetch and
    the static_ids exclusion set are both empty, isolating the lo_ultimo behaviour.
    """
    return {
        "principal":  {"active": False, "article_ids": []},
        "suplemento": {"active": False, "article_ids": []},
        "especial":   {"active": False, "article_ids": []},
        "sections": [],
        "componentes": [lo_ultimo_comp],
    }


class BuildHomeDataLoUltimoSoftPinContractTest(SimpleTestCase):
    """
    Contract: the live render path must NOT soft-pin saved articles.

    Captures the soft_pin_saved flag that build_home_data passes to
    _fetch_component_articles for the lo_ultimo key. It must be False so that only
    explicitly pinned articles are anchored.
    """

    def _captured_soft_pin(self, lo_ultimo_comp):
        captured = {}

        def mock_fetch(key, saved_ids=None, pinned_ids=None, exclude_ids=None,
                       soft_pin_saved=False, **kwargs):
            captured[key] = soft_pin_saved
            return []

        resolved = _empty_static_resolved(lo_ultimo_comp)
        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved), \
             patch("homev4.views.Article") as mock_art, \
             patch("homev4.views._fetch_component_articles", side_effect=mock_fetch), \
             patch("homev4.views._block_active", side_effect=lambda _k, v: bool(v)), \
             patch("homev4.views._SUPLEMENTO_SOURCE_BY_WEEKDAY", {}), \
             patch("homev4.views.timezone") as mock_tz:
            mock_art.published = MagicMock()
            mock_tz.localdate.return_value = _SUNDAY
            mock_tz.now.return_value = _NOW
            build_home_data(resolved, publication=None, layout=None)
        return captured.get("lo_ultimo")

    def test_live_render_requests_dynamic_not_softpin(self):
        """build_home_data must call lo_ultimo with soft_pin_saved=False."""
        comp = {"key": "lo_ultimo", "active": True, "article_ids": [1, 2, 3], "pinned_ids": []}
        self.assertIs(
            self._captured_soft_pin(comp), False,
            "Live home must refresh lo_ultimo dynamically (soft_pin_saved=False); "
            "soft-pinning every saved article freezes the block.",
        )

    def test_live_render_dynamic_even_with_some_pins(self):
        """The flag stays False regardless of how many articles are pinned."""
        comp = {"key": "lo_ultimo", "active": True, "article_ids": [1, 2, 3], "pinned_ids": [2]}
        self.assertIs(self._captured_soft_pin(comp), False)


class BuildHomeDataLoUltimoDynamicRefreshTest(SimpleTestCase):
    """
    End-to-end behaviour through build_home_data with the real
    _fetch_component_articles running against a controlled published set.
    """

    def _run(self, saved_ids, pinned_ids=None, published_ordered=None):
        """Run build_home_data and return the lo_ultimo article ids in order."""
        published_ordered = published_ordered or []
        comp = {
            "key": "lo_ultimo",
            "active": True,
            "article_ids": list(saved_ids or []),
            "pinned_ids": list(pinned_ids or []),
        }
        resolved = _empty_static_resolved(comp)
        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved), \
             patch("homev4.views.Article") as mock_art, \
             patch("homev4.views._block_active", side_effect=lambda _k, v: bool(v)), \
             patch("homev4.views._SUPLEMENTO_SOURCE_BY_WEEKDAY", {}), \
             patch("homev4.views.timezone") as mock_tz:
            mock_art.published = FakeQS(published_ordered)
            mock_tz.localdate.return_value = _SUNDAY
            mock_tz.now.return_value = _NOW
            result = build_home_data(resolved, publication=None, layout=None)
        comps = {c["key"]: c for c in result["componentes"]}
        return [a.id for a in comps["lo_ultimo"]["articles"]]

    def test_unpinned_slots_refresh_with_newest_article(self):
        """No pins: a newer article (4) must enter and the oldest saved (1) drop out."""
        # saved order [1, 2, 3], none pinned; published recency order: 4 (new), 3, 2, 1.
        arts = [_art(4), _art(3), _art(2), _art(1)]
        result = self._run(saved_ids=[1, 2, 3], pinned_ids=[], published_ordered=arts)
        self.assertEqual(
            result, [4, 3, 2],
            "Non-pinned slots must show the 3 most recent articles, not the frozen saved set.",
        )

    def test_pinned_slot_preserved_while_unpinned_refreshes(self):
        """1 pinned stays put; the other two slots pull the newest available articles."""
        # saved [10, 2, 3] with 10 pinned at slot 0; published: 10, 5, 4, 3, 2, 1.
        arts = [_art(10), _art(5), _art(4), _art(3), _art(2), _art(1)]
        result = self._run(saved_ids=[10, 2, 3], pinned_ids=[10], published_ordered=arts)
        self.assertEqual(
            result, [10, 5, 4],
            "Pinned article 10 must hold slot 0 while the non-pinned slots refresh to 5 and 4.",
        )

    def test_all_pinned_block_stays_static(self):
        """When every slot is pinned the block legitimately stays as saved."""
        arts = [_art(30), _art(20), _art(10)]
        result = self._run(saved_ids=[10, 20, 30], pinned_ids=[10, 20, 30], published_ordered=arts)
        self.assertEqual(result, [10, 20, 30])


class BuildEditorDataLoUltimoSoftPinGuardTest(SimpleTestCase):
    """
    Guard for the intentional divergence between the live home and the editor UI.

    The live home (build_home_data) refreshes lo_ultimo dynamically (soft_pin_saved=False).
    The editor UI (build_editor_data) must keep soft_pin_saved=True so the editor still
    sees the saved drag order it is configuring — NOT a dynamically reshuffled list.

    This test fails if a future "consistency" refactor flips the editor to False, which
    would silently break the editor's saved-order display.
    """

    def _captured_soft_pin(self, lo_ultimo_comp):
        captured = {}

        def mock_fetch(key, saved_ids=None, pinned_ids=None, exclude_ids=None,
                       soft_pin_saved=False, **kwargs):
            # Only record the lo_ultimo call coming from the saved-component branch.
            if key == "lo_ultimo" and "lo_ultimo" not in captured:
                captured["lo_ultimo"] = soft_pin_saved
            return []

        resolved = _empty_static_resolved(lo_ultimo_comp)
        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved), \
             patch("homev4.views.Article") as mock_art, \
             patch("homev4.views._fetch_component_articles", side_effect=mock_fetch), \
             patch("homev4.views.timezone") as mock_tz:
            mock_art.published = MagicMock()
            mock_tz.localdate.return_value = _SUNDAY
            mock_tz.now.return_value = _NOW
            build_editor_data(resolved, publication=None)
        return captured.get("lo_ultimo")

    def test_editor_keeps_softpin_saved_order(self):
        """build_editor_data must call lo_ultimo with soft_pin_saved=True."""
        comp = {"key": "lo_ultimo", "active": True, "article_ids": [1, 2, 3], "pinned_ids": [2]}
        self.assertIs(
            self._captured_soft_pin(comp), True,
            "Editor UI must keep soft_pin_saved=True so it displays the saved drag order; "
            "only the live home (build_home_data) refreshes dynamically.",
        )
