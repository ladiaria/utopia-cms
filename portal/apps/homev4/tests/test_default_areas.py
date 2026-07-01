"""
Unit tests (TDD) for adding three verticals to ÁREAS Y PUBLICACIONES.

Task: the áreas block must draw from 16 available verticals (the previous 13 plus
Cotidiana, Libros and Verifica) instead of 13, so the block can still fill its 12
slots — and not leave a visual gap on the home — even when two verticals are taken
away because they are being used as the SUPLEMENTO and the SUPLEMENTO_EXTRA
(Adicional) sources.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.

Two groups:
  1. DefaultAreasMembershipTest: the three new verticals exist in _DEFAULT_AREAS.
  2. NoGapWithSuplementoAndAdicionalTest: end-to-end through build_home_data — with
     both suplemento and adicional active (two sources skipped), the block still
     shows 12 verticals. This fails before the fix (13 - 2 = 11) and passes after
     it (16 - 2 = 14, capped at 12).
"""
import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from homev4.views import _DEFAULT_AREAS, build_home_data


# A known Monday: weekday()=0 → _SUPLEMENTO_SOURCE_BY_WEEKDAY maps to ("publication", "deporte")
_MONDAY = datetime.date(2026, 4, 20)


def _art(article_id):
    """Minimal mock Article with only an id attribute."""
    a = MagicMock()
    a.id = article_id
    return a


def _area_by_slug(slug):
    """Return the _DEFAULT_AREAS entry with the given slug, or None."""
    return next((a for a in _DEFAULT_AREAS if a.get("slug") == slug), None)


class DefaultAreasMembershipTest(SimpleTestCase):
    """The three new verticals must be registered as category areas in _DEFAULT_AREAS."""

    def test_total_is_16_areas(self):
        """_DEFAULT_AREAS grows from 13 to 16 verticals."""
        self.assertEqual(len(_DEFAULT_AREAS), 16)

    def test_cotidiana_present_as_category(self):
        area = _area_by_slug("cotidiana")
        self.assertIsNotNone(area, "cotidiana missing from _DEFAULT_AREAS")
        self.assertEqual(area["type"], "category")
        self.assertEqual(area["name"], "Cotidiana")

    def test_libros_present_as_category(self):
        area = _area_by_slug("libros")
        self.assertIsNotNone(area, "libros missing from _DEFAULT_AREAS")
        self.assertEqual(area["type"], "category")
        self.assertEqual(area["name"], "Libros")

    def test_verifica_present_as_category(self):
        area = _area_by_slug("verifica")
        self.assertIsNotNone(area, "verifica missing from _DEFAULT_AREAS")
        self.assertEqual(area["type"], "category")
        self.assertEqual(area["name"], "Verifica")

    def test_new_areas_do_not_collide_with_existing_slugs(self):
        """The three new slugs must not have been present before (no accidental duplicates)."""
        slugs = [a["slug"] for a in _DEFAULT_AREAS]
        self.assertEqual(len(slugs), len(set(slugs)), "duplicate slug in _DEFAULT_AREAS")

    def test_preexisting_verticals_are_kept(self):
        """Adding the new ones must not drop any of the original 13 verticals."""
        slugs = {a["slug"] for a in _DEFAULT_AREAS}
        for expected in (
            "mundo", "cultura", "local", "deporte", "ambiente", "economia",
            "justicia", "trabajo", "salud", "educacion", "feminismos", "ciencia", "futuro",
        ):
            self.assertIn(expected, slugs)


class NoGapWithSuplementoAndAdicionalTest(SimpleTestCase):
    """
    End-to-end through build_home_data: with suplemento AND suplemento_extra both
    active, their two source verticals are skipped from áreas. With 16 verticals
    available the block still fills all 12 slots (before the fix only 11 remained → gap).
    """

    def _resolved_from_default_areas(self, se_source):
        """Build a resolved grid using the real _DEFAULT_AREAS list, one article each.

        suplemento is active with content (so its Monday source 'deporte' is skipped),
        and suplemento_extra is active with the given (type, slug) source (also skipped).
        """
        sections = [
            {"type": a["type"], "slug": a["slug"], "name": a["name"], "active": True,
             "article_ids": [1000 + i]}
            for i, a in enumerate(_DEFAULT_AREAS)
        ]
        return {
            "principal":  {"active": True, "article_ids": []},
            "suplemento": {"active": True, "article_ids": [99]},  # non-empty → source skip active
            "especial":   {"active": True, "article_ids": []},
            "suplemento_extra": {
                "active": True,
                "source_type": se_source[0],
                "source_slug": se_source[1],
                "article_ids": [98],
            },
            "sections": sections,
            "componentes": [],
        }

    def _run(self, resolved):
        """Run build_home_data with all DB access mocked; return the shown section slugs."""
        def article_filter_mock(*args, **kwargs):
            ids = list(kwargs.get("id__in", []))
            articles = [_art(i) for i in ids]
            qs = MagicMock()
            qs.__iter__ = lambda self: iter(articles)
            qs.select_related.return_value = qs
            qs.prefetch_related.return_value = qs
            return qs

        mock_art = MagicMock()
        mock_art.published.filter.side_effect = article_filter_mock

        with patch("homev4.views.resolve_layout_grid_data", return_value=resolved), \
             patch("homev4.views.Article", mock_art), \
             patch("homev4.views._fetch_component_articles", return_value=[]), \
             patch("homev4.views._block_active", side_effect=lambda _key, val: bool(val)), \
             patch("homev4.views._SUPLEMENTO_SOURCE_BY_WEEKDAY", {0: ("publication", "deporte")}), \
             patch("homev4.views.timezone") as mock_tz:
            mock_tz.localdate.return_value = _MONDAY
            mock_tz.now.return_value = MagicMock()
            result = build_home_data(resolved, publication=None, layout=None)
        return [s["slug"] for s in result.get("sections", [])]

    def test_twelve_shown_when_suplemento_and_adicional_active(self):
        """Both sources skipped → still 12 verticals shown (no gap)."""
        resolved = self._resolved_from_default_areas(se_source=("category", "mundo"))
        shown = self._run(resolved)
        self.assertEqual(len(shown), 12)

    def test_both_source_verticals_excluded_from_areas(self):
        """The suplemento source (deporte) and the adicional source (mundo) must not appear."""
        resolved = self._resolved_from_default_areas(se_source=("category", "mundo"))
        shown = self._run(resolved)
        self.assertNotIn("deporte", shown)
        self.assertNotIn("mundo", shown)

    def test_new_vertical_can_fill_the_freed_slot(self):
        """At least one of the three new verticals reaches the visible top-12, proving the
        block is completed by a new vertical instead of leaving a gap."""
        resolved = self._resolved_from_default_areas(se_source=("category", "mundo"))
        shown = set(self._run(resolved))
        self.assertTrue(
            shown & {"cotidiana", "libros", "verifica"},
            "no new vertical made it into the visible 12 — the gap would remain",
        )
