"""
Regression test for the REAL portada bug QA reports (root cause) — distinct from
the home_top orphan bug (test_principal_home_top_orphan.py).

Before the fix this test FAILED (the carried-over article stayed home_top=False with a
stale position). After the fix, _sync_principal_to_edition reconciles the cover flag +
order for EVERY principal article on the current edition, so it PASSES.

QA's symptom ("se rompe la portada", "quedan fantasmas"):
the order shown in the layout editor (principal block) does NOT match the
"en portada" + "orden" (home_top / top_position) stored on the article's ArticleRel
in the latest edition. The article detail shows no "en portada" / a stale position
while the layout editor shows the article in the principal at position N. Because
refresh_home_layouts_task re-sorts the principal by top_position whenever a journalist
saves an article, this inconsistency reshuffles the home right after 5am
("a la mínima que hagan movimientos se desconfigura todo").

Root cause exercised here — _sync_principal_to_edition only CORRECTS top_position for
articles that ALREADY have home_top=True in the edition (views.py):

    elif article_id not in added_ids:
        ArticleRel.objects.filter(edition=edition, article_id=article_id, home_top=True)
                          .update(top_position=idx + 1)

So a carried-over principal article whose ArticleRel in the *current* edition has
home_top=False is never reconciled: it keeps home_top=False and a stale top_position,
even though the layout editor shows it in the principal at position idx+1.

How an article ends up in the principal with home_top=False in the current edition:
its home_top/top_position was written to a DIFFERENT edition — exactly the weekend bug
confirmed in prod, where the sync wrote to "la diaria" instead of "fin de semana".

Note on test style: the project's test DB is unavailable in this environment, so this
runs the REAL _sync_principal_to_edition against a minimal fake ArticleRel manager that
faithfully implements filter(home_top=...).update(...) semantics. The bug emerges from
the real code's home_top=True filter, not from the fake.
"""
import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from homev4.views import _sync_principal_to_edition


class _Row:
    """Stand-in for an ArticleRel row."""
    def __init__(self, article_id, home_top, top_position):
        self.article_id = article_id
        self.home_top = home_top
        self.top_position = top_position

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

    def order_by(self, *args):
        return self

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeArticleRelManager:
    """Implements just enough of ArticleRel.objects for _sync_principal_to_edition:
    filter() honoring article_id / article_id__in / home_top, plus update()/create()."""
    def __init__(self, store):
        self._store = store

    def filter(self, **kw):
        rows = list(self._store)
        if "article_id" in kw:
            rows = [r for r in rows if r.article_id == kw["article_id"]]
        if "article_id__in" in kw:
            rows = [r for r in rows if r.article_id in kw["article_id__in"]]
        if "home_top" in kw:
            rows = [r for r in rows if r.home_top == kw["home_top"]]
        return _QuerySet(rows)

    def create(self, **kw):
        row = _Row(kw.get("article_id") or kw["article"].id,
                   kw.get("home_top", False), kw.get("top_position"))
        self._store.append(row)
        return row


class _FakeArticleRel:
    def __init__(self, store):
        self.objects = _FakeArticleRelManager(store)


class PrincipalEditionSyncPhantomTest(SimpleTestCase):
    """The layout principal order must be reflected as home_top + top_position on the
    current edition's ArticleRel for EVERY article in the principal — including carried-
    over ones whose row currently has home_top=False."""

    def test_carried_article_with_home_top_false_is_not_reconciled(self):
        A, B = 101, 102

        # Edition rows: B is correctly featured; A is present in the edition but
        # home_top=False (its home_top lives on another edition — the weekend/wrong-
        # edition scenario). Both A and B are in the layout principal.
        store = [
            _Row(B, home_top=True, top_position=1),
            _Row(A, home_top=False, top_position=None),
        ]

        edition = MagicMock()
        edition.articlerel_set.values_list.return_value = [A, B]  # both belong to edition

        layout = MagicMock()

        with patch("homev4.views.timezone") as mock_tz, \
             patch("homev4.views.get_current_edition", return_value=edition), \
             patch("homev4.views.ArticleRel", new=_FakeArticleRel(store)), \
             patch("homev4.views.Publication", MagicMock()), \
             patch("homev4.views._write_audit_log"):
            # Weekday (Wednesday) so the sync targets the publication's own edition.
            mock_tz.localdate.return_value = datetime.date(2026, 6, 10)

            # Editor reorders principal [A, B] -> [B, A]: both carried over, none added
            # or removed. Lists differ, so the sync runs and renumbers positions.
            _sync_principal_to_edition([A, B], [B, A], layout, None)

        rows = {r.article_id: r for r in store}

        # B (already home_top=True) is reconciled fine — control assertion.
        self.assertTrue(rows[B].home_top)
        self.assertEqual(rows[B].top_position, 1)

        # Invariant QA needs: A is in the principal at position 2, so the article detail
        # must show "en portada" with orden 2. It does not — A stays home_top=False with
        # a stale (None) position → "fantasma": el editor dice 2, el artículo dice nada.
        self.assertTrue(
            rows[A].home_top,
            "A está en el principal (pos 2) pero su ArticleRel quedó home_top=False — "
            "fantasma: el editor de layout y el detalle del artículo no coinciden.",
        )
        self.assertEqual(
            rows[A].top_position, 2,
            "A está en el principal en posición 2 pero su top_position no se actualizó "
            "(quedó %s) — el orden del editor no se refleja en la edición." % rows[A].top_position,
        )
