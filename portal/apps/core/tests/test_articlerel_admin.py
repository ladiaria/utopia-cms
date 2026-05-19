"""
Tests for _shift_and_normalize_top_positions (core/admin.py).

Scenarios covered:
- No home_top articles → no-op
- No conflict, no gaps → positions unchanged (already sequential)
- No conflict, pre-existing gaps → gaps closed by normalize
- Conflict at front (position 1) → shift + normalize
- Conflict in middle → shift + normalize
- Conflict at end → shift + normalize
- Pre-existing gaps + conflict → shift + normalize, gaps closed
- Multi-section same edition → edition processed once (no double-shift)
- Multi-edition article → each edition normalized independently
"""

from django.test import TestCase
from django.utils import timezone

from core.models import Article, ArticleRel, Edition, Publication, Section
from core.admin import _shift_and_normalize_top_positions


def _make_pub():
    return Publication.objects.get_or_create(slug="shift-test-pub", defaults={"name": "Shift Test Pub"})[0]


def _make_section():
    return Section.objects.get_or_create(slug="shift-test-sec", defaults={"name": "Shift Test Section"})[0]


def _make_edition(pub, offset_days=0):
    day = timezone.localdate() - timezone.timedelta(days=offset_days)
    return Edition.objects.get_or_create(publication=pub, date_published=day + timezone.timedelta(days=offset_days))[0]


def _make_article(headline):
    return Article.objects.create(headline=headline, type="NE")


def _make_rel(article, edition, section, home_top=True, top_position=None):
    return ArticleRel.objects.create(
        article=article, edition=edition, section=section,
        home_top=home_top, top_position=top_position,
    )


def _positions(edition, section):
    """Return {article_id: top_position} for home_top=True rels in this edition+section."""
    return dict(
        ArticleRel.objects.filter(
            edition=edition, section=section, home_top=True, top_position__isnull=False,
        ).values_list("article_id", "top_position")
    )


class ShiftNormalizeNoOpTest(TestCase):
    """Cases where _shift_and_normalize_top_positions does nothing."""

    def setUp(self):
        self.pub = _make_pub()
        self.sec = _make_section()
        self.ed = Edition.objects.create(
            publication=self.pub, date_published=timezone.localdate()
        )

    def test_no_home_top_rels_is_noop(self):
        """Article with no home_top=True rels → nothing changes."""
        a = _make_article("A")
        _make_rel(a, self.ed, self.sec, home_top=False, top_position=None)
        _shift_and_normalize_top_positions(a)
        # Nothing should have changed — no assertion needed beyond "no crash"
        self.assertEqual(
            ArticleRel.objects.filter(edition=self.ed, home_top=True).count(), 0
        )

    def test_home_top_without_top_position_is_noop(self):
        """home_top=True but top_position=None → not processed."""
        a = _make_article("A")
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=None)
        _shift_and_normalize_top_positions(a)
        # top_position still None
        rel = ArticleRel.objects.get(article=a, edition=self.ed)
        self.assertIsNone(rel.top_position)


class ShiftNormalizeNoConflictTest(TestCase):
    """No conflict cases — normalization still runs."""

    def setUp(self):
        self.pub = _make_pub()
        self.sec = _make_section()
        self.ed = Edition.objects.create(
            publication=self.pub, date_published=timezone.localdate()
        )

    def test_already_sequential_stays_sequential(self):
        """1,2,3 with no conflict → stays 1,2,3."""
        a1 = _make_article("A1")
        a2 = _make_article("A2")
        a3 = _make_article("A3")
        _make_rel(a1, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(a2, self.ed, self.sec, home_top=True, top_position=2)
        _make_rel(a3, self.ed, self.sec, home_top=True, top_position=3)

        # Simulate saving a3 — no conflict
        _shift_and_normalize_top_positions(a3)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(pos[a1.id], 1)
        self.assertEqual(pos[a2.id], 2)
        self.assertEqual(pos[a3.id], 3)

    def test_preexisting_gaps_are_closed(self):
        """A=1, B=4 (gap) → saving A normalizes to A=1, B=2."""
        a = _make_article("A")
        b = _make_article("B")
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(b, self.ed, self.sec, home_top=True, top_position=4)

        _shift_and_normalize_top_positions(a)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(pos[a.id], 1)
        self.assertEqual(pos[b.id], 2)

    def test_new_article_no_conflict_gets_correct_rank(self):
        """A=1, B=2 exist; new C=3 → after normalize C=3, no change to A,B."""
        a = _make_article("A")
        b = _make_article("B")
        c = _make_article("C")
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(b, self.ed, self.sec, home_top=True, top_position=2)
        _make_rel(c, self.ed, self.sec, home_top=True, top_position=3)

        _shift_and_normalize_top_positions(c)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(pos[a.id], 1)
        self.assertEqual(pos[b.id], 2)
        self.assertEqual(pos[c.id], 3)


class ShiftNormalizeConflictTest(TestCase):
    """Conflict cases — shift + normalize."""

    def setUp(self):
        self.pub = _make_pub()
        self.sec = _make_section()
        self.ed = Edition.objects.create(
            publication=self.pub, date_published=timezone.localdate()
        )

    def test_conflict_at_front(self):
        """X=1, A=1, B=2 → X takes 1st, A shifts to 2, B shifts to 3."""
        a = _make_article("A")
        b = _make_article("B")
        x = _make_article("X")
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(b, self.ed, self.sec, home_top=True, top_position=2)
        _make_rel(x, self.ed, self.sec, home_top=True, top_position=1)

        _shift_and_normalize_top_positions(x)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(pos[x.id], 1)
        self.assertEqual(pos[a.id], 2)
        self.assertEqual(pos[b.id], 3)

    def test_conflict_in_middle(self):
        """A=1, B=2, C=3; X=2 → X at 2, B and C shift up."""
        a = _make_article("A")
        b = _make_article("B")
        c = _make_article("C")
        x = _make_article("X")
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(b, self.ed, self.sec, home_top=True, top_position=2)
        _make_rel(c, self.ed, self.sec, home_top=True, top_position=3)
        _make_rel(x, self.ed, self.sec, home_top=True, top_position=2)

        _shift_and_normalize_top_positions(x)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(pos[a.id], 1)
        self.assertEqual(pos[x.id], 2)
        self.assertEqual(pos[b.id], 3)
        self.assertEqual(pos[c.id], 4)

    def test_conflict_at_end(self):
        """A=1, B=2, C=3; X=3 → C shifts, X at 3."""
        a = _make_article("A")
        b = _make_article("B")
        c = _make_article("C")
        x = _make_article("X")
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(b, self.ed, self.sec, home_top=True, top_position=2)
        _make_rel(c, self.ed, self.sec, home_top=True, top_position=3)
        _make_rel(x, self.ed, self.sec, home_top=True, top_position=3)

        _shift_and_normalize_top_positions(x)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(pos[a.id], 1)
        self.assertEqual(pos[b.id], 2)
        self.assertEqual(pos[x.id], 3)
        self.assertEqual(pos[c.id], 4)

    def test_conflict_with_preexisting_gaps(self):
        """A=1, B=4 (gap); X=4 → conflict with B, B shifts to 5, normalize: A=1,X=2,B=3."""
        a = _make_article("A")
        b = _make_article("B")
        x = _make_article("X")
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(b, self.ed, self.sec, home_top=True, top_position=4)
        _make_rel(x, self.ed, self.sec, home_top=True, top_position=4)

        _shift_and_normalize_top_positions(x)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(pos[a.id], 1)
        self.assertEqual(pos[x.id], 2)
        self.assertEqual(pos[b.id], 3)

    def test_successive_conflicts_stay_sequential(self):
        """Multiple saves don't cause unbounded growth: after 3 conflict saves positions are 1..N."""
        a = _make_article("A")
        b = _make_article("B")
        c = _make_article("C")
        d = _make_article("D")
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(b, self.ed, self.sec, home_top=True, top_position=2)
        _make_rel(c, self.ed, self.sec, home_top=True, top_position=3)

        # First conflict: D=1 conflicts with A
        _make_rel(d, self.ed, self.sec, home_top=True, top_position=1)
        _shift_and_normalize_top_positions(d)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(sorted(pos.values()), [1, 2, 3, 4])
        self.assertEqual(pos[d.id], 1)

        # Second conflict: move B to 1 again
        ArticleRel.objects.filter(article=b, edition=self.ed).update(top_position=1)
        _shift_and_normalize_top_positions(b)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(sorted(pos.values()), [1, 2, 3, 4])
        self.assertEqual(pos[b.id], 1)

        # Third conflict: move C to 1
        ArticleRel.objects.filter(article=c, edition=self.ed).update(top_position=1)
        _shift_and_normalize_top_positions(c)

        pos = _positions(self.ed, self.sec)
        self.assertEqual(sorted(pos.values()), [1, 2, 3, 4])
        self.assertEqual(pos[c.id], 1)


class ShiftNormalizeMultiSectionTest(TestCase):
    """Article in multiple sections of the same edition — dedup by edition_id."""

    def setUp(self):
        self.pub = _make_pub()
        self.sec = _make_section()
        self.sec2 = Section.objects.get_or_create(
            slug="shift-test-sec2", defaults={"name": "Shift Test Section 2"}
        )[0]
        self.ed = Edition.objects.create(
            publication=self.pub, date_published=timezone.localdate()
        )

    def test_multi_section_same_edition_processed_once(self):
        """Article X in 2 sections of same edition: no double-shift."""
        a = _make_article("A")
        x = _make_article("X")

        # A is in both sections at position 1
        _make_rel(a, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(a, self.ed, self.sec2, home_top=True, top_position=1)

        # X is also in both sections at position 1 (conflict)
        _make_rel(x, self.ed, self.sec, home_top=True, top_position=1)
        _make_rel(x, self.ed, self.sec2, home_top=True, top_position=1)

        _shift_and_normalize_top_positions(x)

        # Both sections: X=1, A=2 (no double-shifting A to 3+)
        pos_sec1 = _positions(self.ed, self.sec)
        pos_sec2 = _positions(self.ed, self.sec2)
        self.assertEqual(pos_sec1[x.id], 1)
        self.assertEqual(pos_sec1[a.id], 2)
        self.assertEqual(pos_sec2[x.id], 1)
        self.assertEqual(pos_sec2[a.id], 2)


class ShiftNormalizeMultiEditionTest(TestCase):
    """Article in two different editions — each edition normalized independently."""

    def setUp(self):
        self.pub = _make_pub()
        self.sec = _make_section()
        self.ed1 = Edition.objects.create(
            publication=self.pub, date_published=timezone.localdate() - timezone.timedelta(days=1)
        )
        self.ed2 = Edition.objects.create(
            publication=self.pub, date_published=timezone.localdate()
        )

    def test_multi_edition_normalized_independently(self):
        """X in ed1 (pos=1) and ed2 (pos=1); each edition has its own conflict. Both normalize."""
        a = _make_article("A")
        b = _make_article("B")
        x = _make_article("X")

        # ed1: A=1, X=1 (conflict)
        _make_rel(a, self.ed1, self.sec, home_top=True, top_position=1)
        _make_rel(x, self.ed1, self.sec, home_top=True, top_position=1)

        # ed2: B=1, X=1 (conflict)
        _make_rel(b, self.ed2, self.sec, home_top=True, top_position=1)
        _make_rel(x, self.ed2, self.sec, home_top=True, top_position=1)

        _shift_and_normalize_top_positions(x)

        pos1 = _positions(self.ed1, self.sec)
        pos2 = _positions(self.ed2, self.sec)

        self.assertEqual(pos1[x.id], 1)
        self.assertEqual(pos1[a.id], 2)
        self.assertEqual(pos2[x.id], 1)
        self.assertEqual(pos2[b.id], 2)
