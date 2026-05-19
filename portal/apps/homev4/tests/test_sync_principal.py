"""
Unit tests for _sync_principal_to_edition().

This function is called by save_grid() whenever the editor saves changes to the
principal block. It syncs ArticleRel.home_top / top_position so that the
celery:refresh task (which reads Edition.top_articles ordered by top_position)
does not reinsert articles the editor intentionally removed or reordered.

Contract under test:
- No change (old_ids == new_ids)  → no DB writes, no audit log.
- No edition found                → no DB writes, no audit log.
- Removed articles                → ArticleRel updated: home_top=False, top_position=None.
- Articles in new_ids             → ArticleRel updated: home_top=True, top_position=1-based index.
- Reorder only (same set)         → top_position updated, no removal update.
- Audit log                       → written with triggered_by="editor:edition_sync",
                                    ids_before=old_ids, ids_after=new_ids.

All tests use SimpleTestCase — no database required.
"""
from unittest.mock import MagicMock, patch, call

from django.test import SimpleTestCase

from homev4.views import _sync_principal_to_edition


def _run(old_ids, new_ids, edition, layout=None, user=None):
    """Run _sync_principal_to_edition under full mock isolation.

    Returns (mock_article_rel, mock_audit_log) for assertions.
    """
    if layout is None:
        layout = MagicMock()
    if user is None:
        user = MagicMock()
    mock_ar = MagicMock()
    with patch("homev4.views.get_current_edition", return_value=edition), \
         patch("homev4.views.ArticleRel", mock_ar), \
         patch("homev4.views._write_audit_log") as mock_audit:
        _sync_principal_to_edition(old_ids, new_ids, layout, user)
    return mock_ar, mock_audit


# ---------------------------------------------------------------------------
# No-op cases
# ---------------------------------------------------------------------------

class SyncNoOpTest(SimpleTestCase):
    """_sync_principal_to_edition must be a pure no-op when nothing changed."""

    def test_identical_lists_no_articlerel_calls(self):
        """old_ids == new_ids → ArticleRel is never touched."""
        mock_ar, _ = _run([1, 2, 3], [1, 2, 3], MagicMock())
        mock_ar.objects.filter.assert_not_called()

    def test_identical_lists_no_audit_log(self):
        """old_ids == new_ids → no audit log is written."""
        _, mock_audit = _run([1, 2, 3], [1, 2, 3], MagicMock())
        mock_audit.assert_not_called()

    def test_both_empty_no_articlerel_calls(self):
        """Both old and new are empty → nothing to do."""
        mock_ar, _ = _run([], [], MagicMock())
        mock_ar.objects.filter.assert_not_called()

    def test_no_edition_no_articlerel_calls(self):
        """If get_current_edition returns None, ArticleRel is never touched."""
        mock_ar, _ = _run([1, 2], [2, 1], edition=None)
        mock_ar.objects.filter.assert_not_called()

    def test_no_edition_no_audit_log(self):
        """If get_current_edition returns None, no audit log is written."""
        _, mock_audit = _run([1, 2], [2, 1], edition=None)
        mock_audit.assert_not_called()


# ---------------------------------------------------------------------------
# Removal: articles present in old_ids but absent from new_ids
# ---------------------------------------------------------------------------

class SyncRemovalTest(SimpleTestCase):
    """When articles are removed from principal, their home_top must be cleared."""

    def test_removed_article_in_filter_call(self):
        """The removed article ID appears in the article_id__in filter."""
        mock_ar, _ = _run([1, 2, 3], [2, 3], MagicMock())
        removal_call = next(
            (c for c in mock_ar.objects.filter.call_args_list if "article_id__in" in c.kwargs),
            None,
        )
        self.assertIsNotNone(removal_call, "Expected a filter call with article_id__in for removal")
        self.assertIn(1, removal_call.kwargs["article_id__in"])

    def test_kept_articles_not_in_removal_filter(self):
        """Articles that remain in principal are NOT included in the removal update."""
        mock_ar, _ = _run([1, 2, 3], [2, 3], MagicMock())
        removal_call = next(
            (c for c in mock_ar.objects.filter.call_args_list if "article_id__in" in c.kwargs),
            None,
        )
        self.assertIsNotNone(removal_call)
        removed_ids = removal_call.kwargs["article_id__in"]
        self.assertNotIn(2, removed_ids)
        self.assertNotIn(3, removed_ids)

    def test_removal_update_sets_home_top_false(self):
        """The update for removed articles sets home_top=False and top_position=None."""
        mock_ar, _ = _run([10, 20], [10], MagicMock())
        mock_ar.objects.filter.return_value.update.assert_any_call(home_top=False, top_position=None)

    def test_multiple_removed_articles_all_in_one_filter(self):
        """All removed articles are passed together in a single article_id__in filter."""
        mock_ar, _ = _run([1, 2, 3, 4], [1], MagicMock())
        removal_call = next(
            (c for c in mock_ar.objects.filter.call_args_list if "article_id__in" in c.kwargs),
            None,
        )
        self.assertIsNotNone(removal_call)
        self.assertEqual(set(removal_call.kwargs["article_id__in"]), {2, 3, 4})

    def test_reorder_only_no_removal_filter(self):
        """When only the order changes (no article removed), the home_top=False update is skipped."""
        mock_ar, _ = _run([1, 2, 3], [3, 1, 2], MagicMock())
        removal_call = next(
            (c for c in mock_ar.objects.filter.call_args_list if "article_id__in" in c.kwargs),
            None,
        )
        self.assertIsNone(removal_call, "No removal filter expected for a pure reorder")

    def test_all_articles_removed_gives_empty_new_principal(self):
        """Editor clears the whole principal block → all get home_top=False."""
        mock_ar, _ = _run([1, 2, 3], [], MagicMock())
        removal_call = next(
            (c for c in mock_ar.objects.filter.call_args_list if "article_id__in" in c.kwargs),
            None,
        )
        self.assertIsNotNone(removal_call)
        self.assertEqual(set(removal_call.kwargs["article_id__in"]), {1, 2, 3})


# ---------------------------------------------------------------------------
# top_position alignment: new_ids order → 1-based top_position
# ---------------------------------------------------------------------------

class SyncTopPositionTest(SimpleTestCase):
    """ArticleRel.top_position must reflect the 1-based index in new_ids.

    The filter for these updates includes home_top=True so that articles appearing
    in multiple sections of the same edition only have their cover row updated —
    secondary-section rows (home_top=False) are left untouched.
    """

    def test_each_article_gets_individual_filter_call(self):
        """One filter(article_id=X, home_top=True) call is made per article in new_ids."""
        mock_ar, _ = _run([1, 2, 3], [3, 1, 2], MagicMock())
        individual_calls = [
            c for c in mock_ar.objects.filter.call_args_list if "article_id" in c.kwargs
        ]
        article_ids_filtered = [c.kwargs["article_id"] for c in individual_calls]
        self.assertCountEqual(article_ids_filtered, [3, 1, 2])

    def test_filter_for_top_position_update_includes_home_top_true(self):
        """The per-article filter includes home_top=True to protect secondary-section rows."""
        mock_ar, _ = _run([1, 2, 3], [3, 1, 2], MagicMock())
        individual_calls = [
            c for c in mock_ar.objects.filter.call_args_list if "article_id" in c.kwargs
        ]
        for c in individual_calls:
            self.assertTrue(
                c.kwargs.get("home_top"),
                "filter call for top_position update must include home_top=True",
            )

    def test_first_article_gets_top_position_1(self):
        """The first article in new_ids receives top_position=1."""
        mock_ar, _ = _run([5, 6, 7], [7, 5, 6], MagicMock())
        mock_ar.objects.filter.return_value.update.assert_any_call(top_position=1)

    def test_all_positions_assigned_correctly(self):
        """top_position=idx+1 for each article's position in new_ids."""
        mock_ar, _ = _run([1, 2, 3], [3, 1, 2], MagicMock())
        update_calls = mock_ar.objects.filter.return_value.update.call_args_list
        # Collect all top_position values from calls that only set top_position (not the removal call)
        actual_positions = {
            c.kwargs["top_position"]
            for c in update_calls
            if "top_position" in c.kwargs and "home_top" not in c.kwargs
        }
        self.assertEqual(actual_positions, {1, 2, 3})

    def test_secondary_section_row_not_set_to_home_top_true(self):
        """update() for position alignment must NOT set home_top=True.
        This prevents inadvertently enabling the cover flag on secondary-section rows
        of articles that appear in multiple sections of the same edition.
        """
        mock_ar, _ = _run([1, 2], [1, 2], MagicMock())
        # identical lists → early return, no calls at all; use a real change
        mock_ar2, _ = _run([1, 2], [2, 1], MagicMock())
        position_updates = [
            c for c in mock_ar2.objects.filter.return_value.update.call_args_list
            if "top_position" in c.kwargs
        ]
        for c in position_updates:
            self.assertNotIn(
                "home_top", c.kwargs,
                "top_position update must not include home_top — would corrupt multi-section articles",
            )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class SyncAuditLogTest(SimpleTestCase):
    """_sync_principal_to_edition must write an audit log entry for every real change."""

    def test_audit_log_written_on_removal(self):
        """An audit log entry is written when an article is removed."""
        _, mock_audit = _run([1, 2, 3], [2, 3], MagicMock())
        mock_audit.assert_called_once()

    def test_audit_log_written_on_reorder(self):
        """An audit log entry is written when articles are reordered."""
        _, mock_audit = _run([1, 2, 3], [3, 1, 2], MagicMock())
        mock_audit.assert_called_once()

    def test_audit_log_triggered_by_edition_sync(self):
        """The audit log entry uses triggered_by='editor:edition_sync'."""
        _, mock_audit = _run([1, 2], [2, 1], MagicMock())
        args = mock_audit.call_args[0]
        self.assertEqual(args[3], "editor:edition_sync")

    def test_audit_log_ids_before_matches_old_principal(self):
        """The ids_before in the audit log reflects the old principal article_ids."""
        _, mock_audit = _run([10, 20, 30], [20, 30], MagicMock())
        old_grid_arg = mock_audit.call_args[0][1]
        self.assertEqual(old_grid_arg["principal"]["article_ids"], [10, 20, 30])

    def test_audit_log_ids_after_matches_new_principal(self):
        """The ids_after in the audit log reflects the new principal article_ids."""
        _, mock_audit = _run([10, 20, 30], [20, 30], MagicMock())
        new_grid_arg = mock_audit.call_args[0][2]
        self.assertEqual(new_grid_arg["principal"]["article_ids"], [20, 30])

    def test_no_audit_log_on_no_change(self):
        """No audit log when old_ids == new_ids."""
        _, mock_audit = _run([1, 2, 3], [1, 2, 3], MagicMock())
        mock_audit.assert_not_called()

    def test_no_audit_log_when_no_edition(self):
        """No audit log when there is no current edition."""
        _, mock_audit = _run([1, 2], [2], edition=None)
        mock_audit.assert_not_called()

    def test_audit_log_user_passed_as_kwarg(self):
        """The user performing the action is forwarded to the audit log."""
        user = MagicMock()
        _, mock_audit = _run([1, 2], [2, 1], MagicMock(), user=user)
        self.assertEqual(mock_audit.call_args[1].get("user"), user)
