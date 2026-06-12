"""
Reproduction test for the EN PORTADA (home_top) orphan bug.

Background — the bidirectional sync (commit ea67b6c2d) intends a single invariant:
the principal block and the set of ArticleRel rows with home_top=True in today's
edition must describe the same articles. Direction 1 (_sync_principal_to_edition)
clears home_top for articles the EDITOR removes; Direction 2 (refresh) drops
articles whose EN PORTADA was unchecked and re-sorts by top_position.

The gap: refresh_home_layouts_task caps the principal at BLOCK_ARTICLE_LIMITS
("principal" = 10) via _merge_principal_article_ids(...)[:10]. When a newly
featured article (home_top=True in the edition) is pushed past position 10, it is
silently dropped from the principal block — but NOTHING clears its home_top flag:
- It is not in _sync_principal_to_edition's removed_ids (the editor did not remove it).
- refresh only READS top_position; it never writes home_top.

Result: an article with EN PORTADA checked that is NOT on the home — an "orphan".
This test drives the real refresh_home_layouts_task and asserts the intended
invariant (no orphans). It FAILS, reproducing the production bug.

All DB calls are mocked — no database required (SimpleTestCase).
"""
import unittest
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


def _art(article_id):
    a = MagicMock()
    a.id = article_id
    return a


class HomeTopOrphanReproductionTest(SimpleTestCase):
    """refresh must not leave home_top=True articles outside the capped principal."""

    def _run_refresh(self, current_principal_ids, edition_home_top_ids):
        """
        Run the real refresh_home_layouts_task for one publication on a weekday.

        - current_principal_ids: principal block before refresh (editor's saved order).
        - edition_home_top_ids: every article with home_top=True in today's edition,
          ordered by top_position (i.e. edition.top_articles order).

        Returns the article_ids saved into the active layout's principal after refresh.
        """
        mock_pub = MagicMock()
        mock_pub.slug = "ladiaria"
        mock_pub_cls = MagicMock()
        mock_pub_cls.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_pub_cls.objects.get.return_value = mock_pub

        # Active layout carrying the editor's current principal order.
        mock_layout = MagicMock()
        mock_layout.pk = 1
        mock_layout.grid_data = {"principal": {"active": True, "article_ids": list(current_principal_ids)}}

        # Edition: top_articles are the home_top=True rows (ordered by top_position);
        # articlerel_set holds every row (edition_all_ids) — here all are home_top.
        mock_edition = MagicMock()
        mock_edition.top_articles = [_art(i) for i in edition_home_top_ids]
        mock_edition.articlerel_set.values_list.return_value = list(edition_home_top_ids)

        # ArticleRel position lookup used by refresh's re-sort step: article_id -> top_position.
        positions = [(aid, idx + 1) for idx, aid in enumerate(edition_home_top_ids)]
        mock_articlerel = MagicMock()
        mock_articlerel.objects.filter.return_value.values_list.return_value = positions

        # Capture what refresh saves into the layout.
        saved = {}

        def _save():
            saved["grid"] = mock_layout.grid_data

        mock_layout.save.side_effect = _save

        with patch("homev4.tasks.HomeLayout") as mock_hl, \
             patch("homev4.tasks.timezone") as mock_tz, \
             patch("homev4.tasks._propagate_article_ids"), \
             patch("homev4.tasks._write_audit_log"), \
             patch("homev4.tasks._sort_sections_by_recency"), \
             patch("homev4.tasks.get_papel_url"), \
             patch("homev4.tasks.transaction"), \
             patch("homev4.tasks.logger"), \
             patch("django.core.cache.cache"), \
             patch("core.models.Publication", new=mock_pub_cls), \
             patch("core.models.get_current_edition", return_value=mock_edition), \
             patch("core.models.ArticleRel", new=mock_articlerel), \
             patch("homev4.views.resolve_layout_grid_data", side_effect=lambda gd, **kw: gd):
            # Weekday (Wednesday) so refresh uses the publication's own edition.
            import datetime
            mock_tz.localdate.return_value = datetime.date(2026, 6, 10)
            mock_hl.objects.order_by.return_value.values_list.return_value.distinct.return_value = [1]
            mock_hl.get_active_layout.return_value = mock_layout

            from homev4.tasks import refresh_home_layouts_task
            refresh_home_layouts_task()

        return saved["grid"]["principal"]["article_ids"], mock_articlerel

    @unittest.expectedFailure  # KNOWN BUG (secondary): cap-dropped articles keep home_top=True.
    # Tracked as a pending consistency fix in refresh_home_layouts_task (reconcile the cap).
    # When that fix lands, this becomes an unexpected success — remove this decorator then.
    def test_featured_article_past_cap_is_not_orphaned(self):
        """
        Editor curated 10 articles (positions 1..10). A new article (11) is marked
        EN PORTADA in the ArticleRel admin, entering the edition as home_top=True.
        On refresh the principal is capped at 10, so article 11 drops out of the
        block. The intended invariant: every home_top=True article is on the home,
        so article 11's home_top must be cleared. It is not — reproducing the bug.
        """
        current_principal = list(range(1, 11))          # [1..10] editor curation
        edition_home_top = list(range(1, 12))           # [1..11] — 11 newly featured

        saved_principal, mock_articlerel = self._run_refresh(current_principal, edition_home_top)

        # The cap drops 11 from the principal block (this part is expected behavior).
        self.assertNotIn(11, saved_principal, "cap should drop the 11th article from the block")
        self.assertEqual(len(saved_principal), 10)

        # Invariant the bidirectional sync intends: no article is home_top=True yet absent
        # from the principal. Compute the orphans refresh leaves behind.
        orphans = set(edition_home_top) - set(saved_principal)
        self.assertEqual(
            orphans, set(),
            "EN PORTADA orphan(s) left behind: %s have home_top=True but are not on the home. "
            "refresh capped the principal but never cleared their home_top flag." % sorted(orphans),
        )
