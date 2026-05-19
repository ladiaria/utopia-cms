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


# ---------------------------------------------------------------------------
# Helpers for weekend-edition and picker-create tests
# ---------------------------------------------------------------------------

class _FakeArticleDoesNotExist(Exception):
    """Substitute for Article.DoesNotExist when Article itself is mocked."""


def _make_article(has_main_section=True):
    """Return a mock Article with or without a valid main_section link."""
    article = MagicMock()
    if has_main_section:
        article.main_section_id = 1
        article.main_section = MagicMock()
        article.main_section.section = MagicMock()
    else:
        article.main_section_id = None
        article.main_section = None
    return article


def _edition_without(article_ids=()):
    """Return a mock Edition whose articlerel_set reports the given article IDs."""
    edition = MagicMock()
    edition.articlerel_set.values_list.return_value = list(article_ids)
    return edition


def _run_full(old_ids, new_ids, edition, layout=None, user=None,
              weekday=1, mock_article=None, fds_pub="default", article_raises=False):
    """Run _sync_principal_to_edition with extended mock isolation.

    In addition to the patches in _run(), this helper also patches:
    - timezone.localdate      — controlled by weekday (int 0–6)
    - Publication             — .objects.filter().first() returns fds_pub
    - Article                 — .objects.get() returns mock_article or raises DoesNotExist

    fds_pub="default" creates a fresh MagicMock so callers can verify it was used.
    Pass fds_pub=None to simulate "no findesemana publication exists".

    Returns (mock_ar, mock_article_cls, mock_pub, mock_get_edition, mock_audit).
    """
    if layout is None:
        layout = MagicMock()
    if user is None:
        user = MagicMock()
    if fds_pub == "default":
        fds_pub = MagicMock()

    mock_ar = MagicMock()

    mock_article_cls = MagicMock()
    mock_article_cls.DoesNotExist = _FakeArticleDoesNotExist
    if article_raises or mock_article is None:
        mock_article_cls.objects.get.side_effect = _FakeArticleDoesNotExist
    else:
        mock_article_cls.objects.get.return_value = mock_article
        mock_article_cls.objects.get.side_effect = None

    mock_pub = MagicMock()
    mock_pub.objects.filter.return_value.first.return_value = fds_pub

    mock_date = MagicMock()
    mock_date.weekday.return_value = weekday

    with patch("homev4.views.timezone.localdate", return_value=mock_date), \
         patch("homev4.views.get_current_edition", return_value=edition) as mock_get_edition, \
         patch("homev4.views.ArticleRel", mock_ar), \
         patch("homev4.views.Publication", mock_pub), \
         patch("homev4.views.Article", mock_article_cls), \
         patch("homev4.views._write_audit_log") as mock_audit:
        _sync_principal_to_edition(old_ids, new_ids, layout, user)

    return mock_ar, mock_article_cls, mock_pub, mock_get_edition, mock_audit


# ---------------------------------------------------------------------------
# Weekend edition selection
# ---------------------------------------------------------------------------

class SyncWeekendEditionTest(SimpleTestCase):
    """_sync_principal_to_edition must resolve the edition via findesemana on weekends."""

    def test_saturday_uses_findesemana_publication(self):
        """On Saturday (weekday=5) get_current_edition is called with the findesemana pub."""
        fds_pub = MagicMock()
        layout = MagicMock()
        _, _, _, mock_get_edition, _ = _run_full(
            [1, 2], [2, 1], _edition_without([1, 2]),
            layout=layout, weekday=5, fds_pub=fds_pub,
        )
        mock_get_edition.assert_called_once_with(publication=fds_pub)

    def test_sunday_uses_findesemana_publication(self):
        """On Sunday (weekday=6) get_current_edition is called with the findesemana pub."""
        fds_pub = MagicMock()
        layout = MagicMock()
        _, _, _, mock_get_edition, _ = _run_full(
            [1, 2], [2, 1], _edition_without([1, 2]),
            layout=layout, weekday=6, fds_pub=fds_pub,
        )
        mock_get_edition.assert_called_once_with(publication=fds_pub)

    def test_weekday_uses_layout_publication(self):
        """On a weekday (weekday=2) get_current_edition is called with layout.publication."""
        layout = MagicMock()
        _, _, _, mock_get_edition, _ = _run_full(
            [1, 2], [2, 1], _edition_without([1, 2]),
            layout=layout, weekday=2,
        )
        mock_get_edition.assert_called_once_with(publication=layout.publication)

    def test_weekend_no_fds_pub_falls_back_to_layout_publication(self):
        """Weekend with no findesemana publication → falls back to layout.publication."""
        layout = MagicMock()
        _, _, _, mock_get_edition, _ = _run_full(
            [1, 2], [2, 1], _edition_without([1, 2]),
            layout=layout, weekday=6, fds_pub=None,
        )
        mock_get_edition.assert_called_once_with(publication=layout.publication)

    def test_weekend_publication_lookup_uses_findesemana_slug(self):
        """The Publication query on weekends filters by slug='findesemana'."""
        _, _, mock_pub, _, _ = _run_full(
            [1, 2], [2, 1], _edition_without([1, 2]), weekday=5,
        )
        mock_pub.objects.filter.assert_called_once_with(slug="findesemana")

    def test_weekday_skips_publication_lookup(self):
        """On a weekday Publication is never queried (no findesemana lookup)."""
        _, _, mock_pub, _, _ = _run_full(
            [1, 2], [2, 1], _edition_without([1, 2]), weekday=3,
        )
        mock_pub.objects.filter.assert_not_called()


# ---------------------------------------------------------------------------
# Picker ArticleRel creation
# ---------------------------------------------------------------------------

class SyncPickerCreateTest(SimpleTestCase):
    """When a picker-added article is absent from the current edition, an ArticleRel must be
    created so celery:refresh can include it in Edition.top_articles."""

    def test_create_called_for_picker_article_not_in_edition(self):
        """ArticleRel.objects.create is called when the picker article is not in the edition."""
        article = _make_article()
        edition = _edition_without()  # article 99 not present
        mock_ar, _, _, _, _ = _run_full(
            [1, 2], [1, 2, 99], edition, weekday=1, mock_article=article,
        )
        mock_ar.objects.create.assert_called_once()

    def test_create_receives_correct_fields(self):
        """The new ArticleRel has home_top=True, position=1, and the article's main section."""
        article = _make_article()
        edition = _edition_without()
        mock_ar, _, _, _, _ = _run_full(
            [1, 2], [1, 2, 99], edition, weekday=1, mock_article=article,
        )
        mock_ar.objects.create.assert_called_once_with(
            edition=edition,
            article=article,
            section=article.main_section.section,
            position=1,
            home_top=True,
            top_position=3,  # idx=2 → 1-based position 3
        )

    def test_create_top_position_reflects_order_in_new_ids(self):
        """top_position equals the 1-based index of the article in new_ids."""
        article = _make_article()
        edition = _edition_without()
        mock_ar, _, _, _, _ = _run_full(
            [1, 2], [99, 1, 2], edition, weekday=1, mock_article=article,
        )
        mock_ar.objects.create.assert_called_once_with(
            edition=edition,
            article=article,
            section=article.main_section.section,
            position=1,
            home_top=True,
            top_position=1,  # idx=0 → 1-based position 1
        )

    def test_no_create_when_article_has_no_main_section(self):
        """If the article has no main_section, create is skipped (section would be None)."""
        article = _make_article(has_main_section=False)
        edition = _edition_without()
        mock_ar, _, _, _, _ = _run_full(
            [1, 2], [1, 2, 99], edition, weekday=1, mock_article=article,
        )
        mock_ar.objects.create.assert_not_called()

    def test_no_create_when_article_does_not_exist(self):
        """If Article.objects.get raises DoesNotExist, no ArticleRel is created."""
        edition = _edition_without()
        mock_ar, _, _, _, _ = _run_full(
            [1, 2], [1, 2, 99], edition, weekday=1, article_raises=True,
        )
        mock_ar.objects.create.assert_not_called()

    def test_no_create_when_article_already_in_edition(self):
        """If the picker article already belongs to the edition, the existing row is used
        (home_top set via update, not a new create)."""
        article = _make_article()
        edition = _edition_without(article_ids=[99])  # 99 IS in the edition
        mock_ar, _, _, _, _ = _run_full(
            [1, 2], [1, 2, 99], edition, weekday=1, mock_article=article,
        )
        mock_ar.objects.create.assert_not_called()

    def test_multiple_picker_articles_each_get_their_own_create(self):
        """Two picker articles both absent from the edition → two separate create calls."""
        article_a = _make_article()
        article_b = _make_article()
        edition = _edition_without()

        mock_article_cls = MagicMock()
        mock_article_cls.DoesNotExist = _FakeArticleDoesNotExist
        mock_article_cls.objects.get.side_effect = lambda pk: article_a if pk == 88 else article_b

        mock_ar = MagicMock()
        layout = MagicMock()
        mock_date = MagicMock()
        mock_date.weekday.return_value = 1
        mock_pub = MagicMock()

        with patch("homev4.views.timezone.localdate", return_value=mock_date), \
             patch("homev4.views.get_current_edition", return_value=edition), \
             patch("homev4.views.ArticleRel", mock_ar), \
             patch("homev4.views.Publication", mock_pub), \
             patch("homev4.views.Article", mock_article_cls), \
             patch("homev4.views._write_audit_log"):
            _sync_principal_to_edition([1], [1, 88, 99], layout, MagicMock())

        self.assertEqual(mock_ar.objects.create.call_count, 2)
