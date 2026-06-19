"""
TDD reproduction + contract for the "bug portada finde — edición vieja de madrugada"
(reported Saturday 2026-06-13 at 12:09 AM / 00:09).

Reproduced root cause:
  refresh_home_layouts_task() decides whether to inject the weekend "Fin de semana"
  edition into the principal using `timezone.localdate().weekday()`, which flips to
  Saturday at 00:00. But the edition gate (get_current_edition) only flips the
  "current" edition at PUBLISHING_TIME (05:00). During the 00:00–05:00 window the two
  are misaligned, so a refresh resolves the WRONG edition:

    - Saturday 00:00–05:00: weekend branch active, but get_current_edition(findesemana)
      still returns LAST week's edition (date_published < today) -> "viejazo de una
      semana atrás". (This is what the editor saw live at 00:09.)
    - Monday 00:00–05:00: weekday branch active, so it injects FRIDAY's la diaria
      edition into a home that editorially still shows the weekend (Sunday extends to
      Monday 5am). Milder, same class of misalignment.

Desired behavior (the fix this test drives):
  Align the weekend trigger to the SAME 5am gate as the edition: compute the editorial
  day with PUBLISHING_TIME so that before 5am the day is still "yesterday". Then:
    - Saturday pre-5am  -> editorial Friday  -> regular la diaria edition (no stale FDS).
    - Monday pre-5am    -> editorial Sunday  -> this weekend's FDS (consistent, current).
    - Tue–Fri & all daytime -> unchanged.

All tests are SimpleTestCase + mock (no DB), matching the homev4 test convention.
The real _merge_principal_article_ids is left unpatched so the merge actually runs.

Run:
  python -W ignore manage.py test --settings=test_settings --keepdb \
      homev4.tests.test_refresh_weekend_gate
"""
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

# Disjoint ID sets so assertions read clearly.
_FRIDAY_IDS = [801, 802]               # la diaria Friday edition
_TUESDAY_IDS = [701, 702]             # la diaria Tuesday edition (weekday control)
_LAST_WEEK_FDS_IDS = [201, 202, 203]  # previous weekend edition (the stale content)
_THIS_WEEK_FDS_IDS = [301, 302]       # current weekend edition (Saturday-dated)

# Reference days in June 2026.
_SATURDAY = datetime.date(2026, 6, 13)   # weekday() == 5
_MONDAY = datetime.date(2026, 6, 15)     # weekday() == 0
_WEDNESDAY = datetime.date(2026, 6, 17)  # weekday() == 2


def _at(date, hour):
    return datetime.datetime(date.year, date.month, date.day, hour, 0)


def _make_edition(top_ids, all_ids, edid, date_published):
    """Minimal stand-in for a core.models.Edition used by refresh_home_layouts_task."""
    ed = MagicMock()
    ed.id = edid
    ed.date_published = date_published
    ed.top_articles = [SimpleNamespace(id=i) for i in top_ids]            # [a.id for a in edition.top_articles]
    ed.articlerel_set.values_list.return_value = list(all_ids)            # set(edition.articlerel_set.values_list(...))
    return ed


class RefreshWeekendGateTest(SimpleTestCase):
    def _run_refresh(self, localdate, localtime_dt, *, fds_edition, weekday_edition, current_principal):
        """
        Run refresh_home_layouts_task() for one publication. The active layout starts
        with `current_principal`. get_current_edition is mocked to mimic the real gate:
        it returns `fds_edition` for findesemana and `weekday_edition` for la diaria.
        Returns the principal article_ids written to the layout after the task.
        """
        la_diaria_pub = MagicMock(name="la_diaria")
        fds_pub = MagicMock(name="findesemana")

        mock_pub_cls = MagicMock()
        mock_pub_cls.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_pub_cls.objects.get.return_value = la_diaria_pub
        mock_pub_cls.objects.filter.return_value.first.return_value = fds_pub

        def fake_get_current_edition(publication=None, **kw):
            return fds_edition if publication is fds_pub else weekday_edition

        mock_layout = MagicMock()
        mock_layout.pk = 7
        mock_layout.grid_data = {"principal": {"active": True, "article_ids": list(current_principal)}}

        # Empty positions => merge order preserved; we only assert content membership.
        mock_arel = MagicMock()
        mock_arel.objects.filter.return_value.values_list.return_value = []

        mock_tz = MagicMock()
        mock_tz.localdate.return_value = localdate
        mock_tz.localtime.return_value = localtime_dt

        with patch("homev4.tasks.timezone", mock_tz), \
             patch("homev4.tasks.HomeLayout") as mock_hl, \
             patch("homev4.tasks._propagate_article_ids"), \
             patch("homev4.tasks._write_audit_log"), \
             patch("homev4.tasks._sort_sections_by_recency"), \
             patch("homev4.tasks.transaction"), \
             patch("homev4.tasks.logger"), \
             patch("core.models.Publication", new=mock_pub_cls), \
             patch("core.models.get_current_edition", side_effect=fake_get_current_edition), \
             patch("core.models.ArticleRel", new=mock_arel), \
             patch("homev4.views.resolve_layout_grid_data", side_effect=lambda gd, **kw: gd), \
             patch("homev4.views._clear_fallback_blocks", side_effect=lambda gd: gd):

            mock_hl.objects.order_by.return_value.values_list.return_value.distinct.return_value = [1]
            mock_hl.get_active_layout.return_value = mock_layout

            from homev4.tasks import refresh_home_layouts_task
            refresh_home_layouts_task()

        return mock_layout.grid_data.get("principal", {}).get("article_ids", [])

    # ---- Saturday: the reported bug -------------------------------------------------

    def test_saturday_before_5am_does_not_inject_previous_weekend_edition(self):
        """Saturday 00:00–05:00 must NOT pull last week's Fin de semana edition; the
        editorial day is still Friday."""
        last_week_fds = _make_edition(_LAST_WEEK_FDS_IDS, set(_LAST_WEEK_FDS_IDS), 8974, datetime.date(2026, 6, 6))
        friday_ed = _make_edition(_FRIDAY_IDS, set(_FRIDAY_IDS), 8000, datetime.date(2026, 6, 12))
        principal = self._run_refresh(
            _SATURDAY, _at(_SATURDAY, 2), fds_edition=last_week_fds, weekday_edition=friday_ed,
            current_principal=_FRIDAY_IDS,
        )
        for stale in _LAST_WEEK_FDS_IDS:
            self.assertNotIn(stale, principal,
                             "pre-5am Saturday must not inject last week's FDS (id=%s); got %s" % (stale, principal))
        self.assertEqual(sorted(principal), sorted(_FRIDAY_IDS))

    def test_saturday_after_5am_uses_current_weekend_edition(self):
        """CONTROL: from 5am Saturday on, this week's FDS must be used. The fix must not break this."""
        this_week_fds = _make_edition(_THIS_WEEK_FDS_IDS, set(_THIS_WEEK_FDS_IDS), 8992, datetime.date(2026, 6, 13))
        friday_ed = _make_edition(_FRIDAY_IDS, set(_FRIDAY_IDS), 8000, datetime.date(2026, 6, 12))
        principal = self._run_refresh(
            _SATURDAY, _at(_SATURDAY, 6), fds_edition=this_week_fds, weekday_edition=friday_ed,
            current_principal=_THIS_WEEK_FDS_IDS,
        )
        for fresh in _THIS_WEEK_FDS_IDS:
            self.assertIn(fresh, principal,
                          "post-5am Saturday must merge this week's FDS (id=%s); got %s" % (fresh, principal))

    # ---- Monday: the side effect of the fix (must become consistent) ----------------

    def test_monday_before_5am_keeps_current_weekend_not_friday(self):
        """Monday 00:00–05:00 is editorially still Sunday (weekend extends to Monday 5am).
        The fix must keep THIS weekend's FDS and must NOT inject Friday's weekday edition."""
        this_week_fds = _make_edition(_THIS_WEEK_FDS_IDS, set(_THIS_WEEK_FDS_IDS), 8992, datetime.date(2026, 6, 13))
        friday_ed = _make_edition(_FRIDAY_IDS, set(_FRIDAY_IDS), 8000, datetime.date(2026, 6, 12))
        principal = self._run_refresh(
            _MONDAY, _at(_MONDAY, 2), fds_edition=this_week_fds, weekday_edition=friday_ed,
            current_principal=_THIS_WEEK_FDS_IDS,
        )
        for fresh in _THIS_WEEK_FDS_IDS:
            self.assertIn(fresh, principal,
                          "Monday pre-5am must keep this weekend's FDS (id=%s); got %s" % (fresh, principal))
        for fri in _FRIDAY_IDS:
            self.assertNotIn(fri, principal,
                             "Monday pre-5am must not inject Friday's weekday edition (id=%s); got %s" % (fri, principal))

    # ---- Weekday: must be untouched by the fix --------------------------------------

    def test_weekday_before_5am_unaffected(self):
        """CONTROL: a regular weekday pre-5am (Wednesday) must keep using la diaria and
        must never pull the weekend edition — identical before and after the fix."""
        this_week_fds = _make_edition(_THIS_WEEK_FDS_IDS, set(_THIS_WEEK_FDS_IDS), 8992, datetime.date(2026, 6, 13))
        tuesday_ed = _make_edition(_TUESDAY_IDS, set(_TUESDAY_IDS), 8100, datetime.date(2026, 6, 16))
        principal = self._run_refresh(
            _WEDNESDAY, _at(_WEDNESDAY, 2), fds_edition=this_week_fds, weekday_edition=tuesday_ed,
            current_principal=_TUESDAY_IDS,
        )
        self.assertEqual(sorted(principal), sorted(_TUESDAY_IDS))
        for fds_id in _THIS_WEEK_FDS_IDS:
            self.assertNotIn(fds_id, principal,
                             "weekday pre-5am must never pull the weekend edition (id=%s); got %s" % (fds_id, principal))
