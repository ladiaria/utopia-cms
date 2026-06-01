"""
Unit tests for resolve_daily_layouts_task behavior in the pending_grid_data path.

The gate tests (test_resolve_daily_gate.py) only verify the time window; they mock
HomeLayout with an empty publications list so the task body never runs. These tests
cover the actual content-injection behavior inside the task.

Bug documented here:
  When an editor prepares the layout in advance (pending_grid_data), the task applies
  that grid and does `continue`, skipping the suplemento and extra_articles injection
  that the non-pending path does. On Saturday this means FSNewsletter articles never
  appear on the home — even though _resolve_extra_article_ids() is called and returns
  the correct IDs before the pending check.

All tests use SimpleTestCase + unittest.mock — no database required.
"""

import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

_SATURDAY = datetime.date(2026, 4, 25)   # weekday() == 5
_SATURDAY_5AM = datetime.datetime(2026, 4, 25, 5, 0, 0, tzinfo=datetime.timezone.utc)


def _make_pub_cls(mock_instance):
    """Return a fake Publication class with a real DoesNotExist and a configured objects.get."""
    cls = MagicMock()
    cls.DoesNotExist = type("DoesNotExist", (Exception,), {})
    cls.objects.get.return_value = mock_instance
    return cls


class ResolveDailyTaskPendingPathTest(SimpleTestCase):
    """
    resolve_daily_layouts_task must inject suplemento and extra_articles into the
    pending grid before saving — the same blocks the non-pending path resolves.
    """

    def _run_task_pending(self, today, localtime_dt, suplemento_ids, extra_ids, pending_grid):
        """
        Run resolve_daily_layouts_task with one publication that has pending_grid_data.
        Returns the mock active layout so callers can inspect grid_data after the task.
        """
        mock_pub = MagicMock()
        mock_pub_cls = _make_pub_cls(mock_pub)

        mock_pending_layout = MagicMock()
        mock_pending_layout.pending_grid_data = {"date": today.isoformat(), "grid": pending_grid}

        mock_active_layout = MagicMock()
        mock_active_layout.grid_data = {}

        with patch("homev4.tasks.timezone.localtime", return_value=localtime_dt), \
             patch("homev4.tasks.timezone.localdate", return_value=today), \
             patch("homev4.tasks._resolve_suplemento_ids", return_value=suplemento_ids), \
             patch("homev4.tasks._resolve_extra_article_ids", return_value=extra_ids), \
             patch("homev4.tasks._propagate_article_ids"), \
             patch("homev4.tasks._write_audit_log"), \
             patch("homev4.tasks.get_papel_url"), \
             patch("homev4.tasks.transaction"), \
             patch("homev4.tasks.logger"), \
             patch("django.core.cache.cache"), \
             patch("homev4.tasks.HomeLayout") as mock_hl, \
             patch("core.models.Publication", new=mock_pub_cls):

            mock_hl.objects.order_by.return_value.values_list.return_value.distinct.return_value = [1]
            mock_hl.objects.filter.return_value.first.return_value = mock_pending_layout
            mock_hl.get_active_layout.return_value = mock_active_layout

            from homev4.tasks import resolve_daily_layouts_task
            resolve_daily_layouts_task()

        return mock_active_layout

    def test_pending_saturday_extra_articles_injected(self):
        """
        On Saturday, extra_articles from FSNewsletter must be written into pending_grid
        before it is saved as grid_data. The editor may have prepared the layout on Friday
        when FSNewsletter did not yet exist, so extra_articles is absent from the saved
        pending. At 5am the task already has the resolved extra_ids — it must use them.
        """
        layout = self._run_task_pending(
            today=_SATURDAY,
            localtime_dt=_SATURDAY_5AM,
            suplemento_ids=[],
            extra_ids=[10, 20, 30],
            pending_grid={
                "principal": {"article_ids": [1, 2]},
                "suplemento": {"article_ids": []},
            },
        )
        saved = layout.grid_data
        self.assertIn("extra_articles", saved, "extra_articles block must be present in saved grid")
        self.assertEqual(saved["extra_articles"]["article_ids"], [10, 20, 30])

    def test_pending_saturday_extra_block_active_flag_preserved(self):
        """
        When pending_grid already contains an extra_articles block (e.g. active=False set
        by the editor), the task must update article_ids but preserve the active flag.
        """
        layout = self._run_task_pending(
            today=_SATURDAY,
            localtime_dt=_SATURDAY_5AM,
            suplemento_ids=[],
            extra_ids=[10, 20],
            pending_grid={
                "principal": {"article_ids": [1]},
                "suplemento": {"article_ids": []},
                "extra_articles": {"active": False, "article_ids": []},
            },
        )
        saved = layout.grid_data
        self.assertEqual(saved["extra_articles"]["article_ids"], [10, 20])
        self.assertFalse(
            saved["extra_articles"].get("active", True),
            "active=False set by the editor must survive the task injection",
        )

    def test_pending_saturday_suplemento_overwritten(self):
        """
        Saturday has no suplemento source so _resolve_suplemento_ids returns [].
        The pending path must overwrite the pending suplemento (which may contain
        Friday's articles) with the resolved empty list — matching the non-pending path.
        """
        layout = self._run_task_pending(
            today=_SATURDAY,
            localtime_dt=_SATURDAY_5AM,
            suplemento_ids=[],  # Saturday has no suplemento source
            extra_ids=[],
            pending_grid={
                "principal": {"article_ids": [1]},
                "suplemento": {"active": True, "article_ids": [5, 6, 7]},  # leftover from Friday
            },
        )
        saved = layout.grid_data
        self.assertEqual(
            saved["suplemento"]["article_ids"],
            [],
            "Friday's suplemento IDs must be cleared when applying Saturday's pending grid",
        )
