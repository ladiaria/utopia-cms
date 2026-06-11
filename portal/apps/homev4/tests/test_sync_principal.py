"""
Outcome-based tests for _sync_principal_to_edition().

This function runs when the editor saves the principal block. It writes the cover flag
(home_top) and order (top_position) onto the CURRENT edition's ArticleRel rows so that
celery:refresh — which reads Edition.top_articles (home_top=True, ordered by top_position)
— preserves the editor's order instead of reverting it.

Contract under test (what the function must GUARANTEE, regardless of how):
- old_ids == new_ids, or no current edition          → no DB writes, no audit log.
- Article removed from principal                      → its row: home_top=False, top_position=None.
- Article kept/reordered/added that IS in the edition → its (primary) row: home_top=True,
                                                         top_position = 1-based index in new_ids.
- Article in principal but NOT in the edition         → a new ArticleRel is created with
                                                         home_top=True + that position.
- Multi-section article                               → only the primary (lowest-position) row
                                                         becomes the cover; secondary rows untouched.
- Weekend                                             → edition resolved via the "findesemana" pub.
- Audit log                                           → one entry, triggered_by="editor:edition_sync",
                                                         ids_before/after = old/new, user forwarded.

These tests assert the resulting ArticleRel state via a minimal fake ORM (no DB, no call-pattern
coupling) so they survive internal refactors of the function.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from homev4.views import _sync_principal_to_edition


class _FakeArticleDoesNotExist(Exception):
    """Substitute for Article.DoesNotExist when Article is mocked."""


# ---------------------------------------------------------------------------
# Minimal fake ORM — implements only what _sync_principal_to_edition uses.
# ---------------------------------------------------------------------------

class _Row:
    """Stand-in for an ArticleRel row in one edition."""
    def __init__(self, article_id, *, home_top=False, top_position=None, position=1, section=None):
        self.article_id = article_id
        self.home_top = home_top
        self.top_position = top_position
        self.position = position
        self.section = section

    def save(self, **kwargs):
        # Attributes are mutated in place on the shared store object; nothing to persist.
        pass


class _QuerySet:
    def __init__(self, rows):
        self._rows = rows

    def update(self, **changes):
        for r in self._rows:
            for field, value in changes.items():
                setattr(r, field, value)
        return len(self._rows)

    def order_by(self, field):
        key = field.lstrip("-")
        return _QuerySet(sorted(self._rows, key=lambda r: getattr(r, key), reverse=field.startswith("-")))

    def first(self):
        return self._rows[0] if self._rows else None


class _ArticleRelManager:
    def __init__(self, store):
        self.store = store
        self.create_calls = []

    def filter(self, **kw):
        rows = list(self.store)  # single edition in the store; edition kwarg is a no-op
        if "article_id" in kw:
            rows = [r for r in rows if r.article_id == kw["article_id"]]
        if "article_id__in" in kw:
            ids = set(kw["article_id__in"])
            rows = [r for r in rows if r.article_id in ids]
        if "home_top" in kw:
            rows = [r for r in rows if r.home_top == kw["home_top"]]
        return _QuerySet(rows)

    def create(self, **kw):
        self.create_calls.append(kw)
        row = _Row(
            kw.get("article_id") or kw["article"].id,
            home_top=kw.get("home_top", False),
            top_position=kw.get("top_position"),
            position=kw.get("position", 1),
            section=kw.get("section"),
        )
        self.store.append(row)
        return row


class _FakeArticleRel:
    def __init__(self, store):
        self.objects = _ArticleRelManager(store)


class _FakeEdition:
    def __init__(self, store, edition_id=1):
        self._store = store
        self.id = edition_id

    @property
    def articlerel_set(self):
        store = self._store

        class _Rel:
            def values_list(self, *args, **kwargs):
                return [r.article_id for r in store]

        return _Rel()


def _make_article(article_id=None, has_main_section=True):
    """Mock Article for the create branch (article not yet in the edition)."""
    article = MagicMock()
    article.id = article_id
    if has_main_section:
        article.main_section_id = 1
        article.main_section.section = MagicMock()
    else:
        article.main_section_id = None
        article.main_section = None
    return article


def _run(old_ids, new_ids, *, rows=None, edition_present=True, weekday=2,
         fds_pub="__make__", article=None, article_raises=False, user=None, layout=None):
    """Run _sync_principal_to_edition against the fake ORM.

    rows: initial _Row objects in the current edition (defaults to empty).
    Returns a namespace with store, manager (for create_calls), and the patched mocks.
    """
    store = list(rows) if rows else []
    edition = _FakeEdition(store) if edition_present else None
    fake_ar = _FakeArticleRel(store)
    layout = layout or MagicMock()
    user = user or MagicMock()
    if fds_pub == "__make__":
        fds_pub = MagicMock()

    article_cls = MagicMock()
    article_cls.DoesNotExist = _FakeArticleDoesNotExist
    if article_raises:
        article_cls.objects.get.side_effect = _FakeArticleDoesNotExist
    else:
        article_cls.objects.get.return_value = article if article is not None else _make_article()

    pub_cls = MagicMock()
    pub_cls.objects.filter.return_value.first.return_value = fds_pub

    tz = MagicMock()
    tz.localdate.return_value.weekday.return_value = weekday

    with patch("homev4.views.timezone", tz), \
         patch("homev4.views.get_current_edition", return_value=edition) as get_ed, \
         patch("homev4.views.ArticleRel", fake_ar), \
         patch("homev4.views.Publication", pub_cls), \
         patch("homev4.views.Article", article_cls), \
         patch("homev4.views._write_audit_log") as audit:
        _sync_principal_to_edition(old_ids, new_ids, layout, user)

    return SimpleNamespace(
        store=store, edition=edition, manager=fake_ar.objects,
        audit=audit, get_edition=get_ed, pub=pub_cls, layout=layout, user=user,
    )


def _by_id(store, article_id):
    """Return the single row for article_id (fails the lookup if absent/duplicated unexpectedly)."""
    matches = [r for r in store if r.article_id == article_id]
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# No-op cases
# ---------------------------------------------------------------------------

class SyncNoOpTest(SimpleTestCase):
    def test_identical_lists_no_writes(self):
        rows = [_Row(1, home_top=True, top_position=1)]
        ctx = _run([1], [1], rows=rows)
        self.assertEqual(ctx.manager.create_calls, [])
        self.assertTrue(_by_id(ctx.store, 1).home_top)
        self.assertEqual(_by_id(ctx.store, 1).top_position, 1)
        ctx.audit.assert_not_called()

    def test_both_empty_no_audit(self):
        ctx = _run([], [])
        ctx.audit.assert_not_called()

    def test_no_edition_no_writes(self):
        rows = [_Row(1, home_top=True, top_position=1)]
        ctx = _run([1, 2], [2, 1], rows=rows, edition_present=False)
        # nothing changed and no audit when there is no current edition
        self.assertEqual(_by_id(ctx.store, 1).top_position, 1)
        ctx.audit.assert_not_called()


# ---------------------------------------------------------------------------
# Removal
# ---------------------------------------------------------------------------

class SyncRemovalTest(SimpleTestCase):
    def test_removed_article_cover_cleared(self):
        rows = [_Row(1, home_top=True, top_position=1), _Row(2, home_top=True, top_position=2)]
        ctx = _run([1, 2], [1], rows=rows)
        removed = _by_id(ctx.store, 2)
        self.assertFalse(removed.home_top)
        self.assertIsNone(removed.top_position)

    def test_kept_article_stays_cover(self):
        rows = [_Row(1, home_top=True, top_position=1), _Row(2, home_top=True, top_position=2)]
        ctx = _run([1, 2], [1], rows=rows)
        kept = _by_id(ctx.store, 1)
        self.assertTrue(kept.home_top)
        self.assertEqual(kept.top_position, 1)

    def test_all_removed_clears_all(self):
        rows = [_Row(1, home_top=True, top_position=1), _Row(2, home_top=True, top_position=2)]
        ctx = _run([1, 2], [], rows=rows)
        self.assertFalse(_by_id(ctx.store, 1).home_top)
        self.assertFalse(_by_id(ctx.store, 2).home_top)

    def test_reorder_does_not_clear_any_cover(self):
        rows = [_Row(1, home_top=True, top_position=1), _Row(2, home_top=True, top_position=2)]
        ctx = _run([1, 2], [2, 1], rows=rows)
        self.assertTrue(_by_id(ctx.store, 1).home_top)
        self.assertTrue(_by_id(ctx.store, 2).home_top)


# ---------------------------------------------------------------------------
# top_position alignment (reorder)
# ---------------------------------------------------------------------------

class SyncTopPositionTest(SimpleTestCase):
    def test_reorder_assigns_1_based_positions(self):
        rows = [
            _Row(1, home_top=True, top_position=1),
            _Row(2, home_top=True, top_position=2),
            _Row(3, home_top=True, top_position=3),
        ]
        ctx = _run([1, 2, 3], [3, 1, 2], rows=rows)
        self.assertEqual(_by_id(ctx.store, 3).top_position, 1)
        self.assertEqual(_by_id(ctx.store, 1).top_position, 2)
        self.assertEqual(_by_id(ctx.store, 2).top_position, 3)

    def test_first_article_gets_position_1(self):
        rows = [_Row(5, home_top=True, top_position=2), _Row(6, home_top=True, top_position=1)]
        ctx = _run([6, 5], [5, 6], rows=rows)  # reorder so 5 moves to the front
        self.assertEqual(_by_id(ctx.store, 5).top_position, 1)


# ---------------------------------------------------------------------------
# The fix: carried-over articles must be reconciled on the current edition
# ---------------------------------------------------------------------------

class SyncCarriedOverReconcileTest(SimpleTestCase):
    """Regression for the "fantasma" bug: a carried-over principal article whose cover flag
    is NOT set on the current edition must be reconciled (home_top=True + position), not skipped.
    """

    def test_carried_article_with_home_top_false_in_edition_is_reconciled(self):
        # A is in the edition but not featured (its cover flag lived on another edition).
        rows = [_Row(2, home_top=True, top_position=1), _Row(1, home_top=False, top_position=None)]
        ctx = _run([2, 1], [1, 2], rows=rows)
        a = _by_id(ctx.store, 1)
        self.assertTrue(a.home_top, "carried article must be set home_top=True on the current edition")
        self.assertEqual(a.top_position, 1)

    def test_carried_article_not_in_edition_is_created(self):
        # B is in the edition; A is in the principal but has NO row in the current edition.
        rows = [_Row(2, home_top=True, top_position=1)]
        article = _make_article(article_id=1)
        ctx = _run([2, 1], [1, 2], rows=rows, article=article)
        self.assertEqual(len(ctx.manager.create_calls), 1, "missing-from-edition article must be created")
        created = _by_id(ctx.store, 1)
        self.assertIsNotNone(created)
        self.assertTrue(created.home_top)
        self.assertEqual(created.top_position, 1)


# ---------------------------------------------------------------------------
# Added articles
# ---------------------------------------------------------------------------

class SyncAddedTest(SimpleTestCase):
    def test_added_article_in_edition_becomes_cover(self):
        rows = [_Row(7, home_top=False, top_position=None)]
        ctx = _run([], [7], rows=rows)
        row = _by_id(ctx.store, 7)
        self.assertTrue(row.home_top)
        self.assertEqual(row.top_position, 1)
        self.assertEqual(ctx.manager.create_calls, [])

    def test_added_article_not_in_edition_is_created(self):
        article = _make_article(article_id=99)
        ctx = _run([], [99], rows=[], article=article)
        self.assertEqual(len(ctx.manager.create_calls), 1)


# ---------------------------------------------------------------------------
# Picker create details
# ---------------------------------------------------------------------------

class SyncPickerCreateTest(SimpleTestCase):
    def test_create_receives_correct_fields(self):
        article = _make_article(article_id=99)
        ctx = _run([1, 2], [1, 2, 99], rows=[_Row(1, home_top=True, top_position=1),
                                             _Row(2, home_top=True, top_position=2)],
                   article=article)
        self.assertEqual(len(ctx.manager.create_calls), 1)
        call = ctx.manager.create_calls[0]
        self.assertEqual(call["edition"], ctx.edition)
        self.assertEqual(call["article"], article)
        self.assertEqual(call["section"], article.main_section.section)
        self.assertEqual(call["position"], 1)
        self.assertTrue(call["home_top"])
        self.assertEqual(call["top_position"], 3)  # idx 2 → 1-based 3

    def test_no_create_when_article_already_in_edition(self):
        rows = [_Row(1, home_top=True, top_position=1), _Row(2, home_top=True, top_position=2),
                _Row(99, home_top=False, top_position=None)]
        ctx = _run([1, 2], [1, 2, 99], rows=rows)
        self.assertEqual(ctx.manager.create_calls, [])
        self.assertTrue(_by_id(ctx.store, 99).home_top)

    def test_no_create_when_article_has_no_main_section(self):
        article = _make_article(article_id=99, has_main_section=False)
        ctx = _run([1], [1, 99], rows=[_Row(1, home_top=True, top_position=1)], article=article)
        self.assertEqual(ctx.manager.create_calls, [])

    def test_no_create_when_article_does_not_exist(self):
        ctx = _run([1], [1, 99], rows=[_Row(1, home_top=True, top_position=1)], article_raises=True)
        self.assertEqual(ctx.manager.create_calls, [])

    def test_multiple_picker_articles_each_created(self):
        ctx = _run([1], [1, 88, 99], rows=[_Row(1, home_top=True, top_position=1)])
        self.assertEqual(len(ctx.manager.create_calls), 2)


# ---------------------------------------------------------------------------
# Multi-section: cover lands on the primary (lowest-position) row only
# ---------------------------------------------------------------------------

class SyncMultiSectionTest(SimpleTestCase):
    def test_only_primary_row_becomes_cover(self):
        # Article 1 appears in two sections of the edition: primary (position 1) and
        # secondary (position 2). Only the primary row must become the cover.
        primary = _Row(1, home_top=False, top_position=None, position=1)
        secondary = _Row(1, home_top=False, top_position=None, position=2)
        ctx = _run([2], [1, 2], rows=[_Row(2, home_top=True, top_position=2), primary, secondary])
        self.assertTrue(primary.home_top, "primary (lowest-position) row must become the cover")
        self.assertEqual(primary.top_position, 1)
        self.assertFalse(secondary.home_top, "secondary-section row must NOT be enabled as cover")
        self.assertIsNone(secondary.top_position)


# ---------------------------------------------------------------------------
# Weekend edition selection
# ---------------------------------------------------------------------------

class SyncWeekendEditionTest(SimpleTestCase):
    def _rows(self):
        return [_Row(1, home_top=True, top_position=1), _Row(2, home_top=True, top_position=2)]

    def test_saturday_uses_findesemana_publication(self):
        fds_pub = MagicMock()
        ctx = _run([1, 2], [2, 1], rows=self._rows(), weekday=5, fds_pub=fds_pub)
        ctx.get_edition.assert_called_once_with(publication=fds_pub)

    def test_sunday_uses_findesemana_publication(self):
        fds_pub = MagicMock()
        ctx = _run([1, 2], [2, 1], rows=self._rows(), weekday=6, fds_pub=fds_pub)
        ctx.get_edition.assert_called_once_with(publication=fds_pub)

    def test_weekday_uses_layout_publication(self):
        ctx = _run([1, 2], [2, 1], rows=self._rows(), weekday=2)
        ctx.get_edition.assert_called_once_with(publication=ctx.layout.publication)

    def test_weekend_no_fds_pub_falls_back_to_layout_publication(self):
        ctx = _run([1, 2], [2, 1], rows=self._rows(), weekday=6, fds_pub=None)
        ctx.get_edition.assert_called_once_with(publication=ctx.layout.publication)

    def test_weekend_publication_lookup_uses_findesemana_slug(self):
        ctx = _run([1, 2], [2, 1], rows=self._rows(), weekday=5)
        ctx.pub.objects.filter.assert_called_once_with(slug="findesemana")

    def test_weekday_skips_publication_lookup(self):
        ctx = _run([1, 2], [2, 1], rows=self._rows(), weekday=3)
        ctx.pub.objects.filter.assert_not_called()


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class SyncAuditLogTest(SimpleTestCase):
    def _rows(self):
        return [_Row(1, home_top=True, top_position=1),
                _Row(2, home_top=True, top_position=2),
                _Row(3, home_top=True, top_position=3)]

    def test_audit_written_on_removal(self):
        ctx = _run([1, 2, 3], [2, 3], rows=self._rows())
        ctx.audit.assert_called_once()

    def test_audit_written_on_reorder(self):
        ctx = _run([1, 2, 3], [3, 1, 2], rows=self._rows())
        ctx.audit.assert_called_once()

    def test_audit_triggered_by_edition_sync(self):
        ctx = _run([1, 2], [2, 1], rows=self._rows())
        self.assertEqual(ctx.audit.call_args[0][3], "editor:edition_sync")

    def test_audit_ids_before_and_after(self):
        ctx = _run([1, 2, 3], [2, 3], rows=self._rows())
        self.assertEqual(ctx.audit.call_args[0][1]["principal"]["article_ids"], [1, 2, 3])
        self.assertEqual(ctx.audit.call_args[0][2]["principal"]["article_ids"], [2, 3])

    def test_audit_user_forwarded(self):
        user = MagicMock()
        ctx = _run([1, 2], [2, 1], rows=self._rows(), user=user)
        self.assertEqual(ctx.audit.call_args[1].get("user"), user)

    def test_no_audit_on_no_change(self):
        ctx = _run([1, 2, 3], [1, 2, 3], rows=self._rows())
        ctx.audit.assert_not_called()

    def test_no_audit_when_no_edition(self):
        ctx = _run([1, 2], [2], rows=self._rows(), edition_present=False)
        ctx.audit.assert_not_called()
