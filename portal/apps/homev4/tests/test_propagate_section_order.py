"""
Unit tests for _propagate_article_ids section ordering.

When refresh_home_layouts_task runs it sorts the active layout's sections by article
recency and then calls _propagate_article_ids. The propagation copies the section ORDER
from source to each sibling so all layouts stay in sync without extra DB queries —
re-sorting each sibling independently would fire N identical queries since all siblings
receive the same article_ids from propagation.

All DB access is mocked — no database required.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from homev4.views import _propagate_article_ids


def _layout(pk, sections):
    """
    Build a minimal mock HomeLayout.
    sections: list of (slug, article_ids) tuples defining both order and content.
    """
    layout = MagicMock()
    layout.pk = pk
    layout.publication = MagicMock()
    layout.grid_data = {
        "sections": [
            {"slug": slug, "article_ids": list(ids), "active": True}
            for slug, ids in sections
        ],
        "principal": {"active": True, "article_ids": []},
        "suplemento": {"active": False, "article_ids": []},
    }
    return layout


class PropagateArticleIdsSectionOrderTest(SimpleTestCase):

    def _run(self, source, siblings):
        with patch("homev4.views.HomeLayout") as MockHL, \
             patch("homev4.views._write_audit_log"):
            MockHL.objects.select_for_update.return_value.exclude.return_value.filter.return_value = siblings
            MockHL.objects.bulk_update = MagicMock()
            _propagate_article_ids(source, source.grid_data)

    def test_sibling_sections_reordered_to_match_source(self):
        """After propagation, sibling section order matches source layout's order."""
        source = _layout(1, [("feminismos", [10]), ("futuro", [20]), ("cultura", [30])])
        sibling = _layout(2, [("futuro", [99]), ("feminismos", [88]), ("cultura", [77])])

        self._run(source, [sibling])

        result = [s["slug"] for s in sibling.grid_data["sections"]]
        self.assertEqual(result, ["feminismos", "futuro", "cultura"])

    def test_sibling_article_ids_propagated(self):
        """Article IDs from source are written into each sibling section."""
        source = _layout(1, [("mundo", [10, 11]), ("cultura", [20, 21])])
        sibling = _layout(2, [("cultura", [999]), ("mundo", [888])])

        self._run(source, [sibling])

        by_slug = {s["slug"]: s["article_ids"] for s in sibling.grid_data["sections"]}
        self.assertEqual(by_slug["mundo"], [10, 11])
        self.assertEqual(by_slug["cultura"], [20, 21])

    def test_extra_section_in_sibling_appended_at_end(self):
        """A section in the sibling but absent from source is appended after the reordered ones."""
        source = _layout(1, [("mundo", [10]), ("cultura", [20])])
        sibling = _layout(2, [("cultura", [99]), ("mundo", [88]), ("futuro", [77])])

        self._run(source, [sibling])

        result = [s["slug"] for s in sibling.grid_data["sections"]]
        self.assertEqual(result[:2], ["mundo", "cultura"])
        self.assertEqual(result[-1], "futuro")

    def test_sibling_missing_source_section_is_skipped(self):
        """A section present in source but absent from sibling is skipped silently."""
        source = _layout(1, [("mundo", [10]), ("cultura", [20]), ("deporte", [30])])
        sibling = _layout(2, [("mundo", [99]), ("cultura", [88])])

        self._run(source, [sibling])

        result = [s["slug"] for s in sibling.grid_data["sections"]]
        self.assertEqual(result, ["mundo", "cultura"])
        self.assertNotIn("deporte", result)

    def test_multiple_siblings_all_reordered(self):
        """All sibling layouts receive the source's section order."""
        source = _layout(1, [("a", [1]), ("b", [2]), ("c", [3])])
        siblings = [
            _layout(2, [("c", [9]), ("b", [8]), ("a", [7])]),
            _layout(3, [("b", [6]), ("a", [5]), ("c", [4])]),
        ]

        self._run(source, siblings)

        for sibling in siblings:
            result = [s["slug"] for s in sibling.grid_data["sections"]]
            self.assertEqual(result, ["a", "b", "c"])

    def test_order_and_ids_both_correct_after_propagation(self):
        """Section order AND article_ids are both correct after propagation."""
        source = _layout(1, [("salud", [5, 6]), ("deporte", [7, 8])])
        sibling = _layout(2, [("deporte", [99]), ("salud", [88])])

        self._run(source, [sibling])

        result_slugs = [s["slug"] for s in sibling.grid_data["sections"]]
        result_ids = {s["slug"]: s["article_ids"] for s in sibling.grid_data["sections"]}
        self.assertEqual(result_slugs, ["salud", "deporte"])
        self.assertEqual(result_ids["salud"], [5, 6])
        self.assertEqual(result_ids["deporte"], [7, 8])
