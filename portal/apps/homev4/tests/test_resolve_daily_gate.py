"""
Unit tests for the time-gate in resolve_daily_layouts_task.

The gate prevents django_celery_beat from publishing pending_grid_data early
when the beat fires the task outside its scheduled 5am window (a known quirk
after multiple beat restarts). Only times in the 4:30–6:00 local window are
allowed to proceed; all others are skipped with a warning log.

All tests use SimpleTestCase + unittest.mock — no database required.
"""

import datetime
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase


def _make_localtime(hour, minute=0):
    """Return a timezone-aware datetime for the given local hour:minute."""
    import django.utils.timezone as tz
    dt = datetime.datetime(2026, 5, 18, hour, minute, 0,
                           tzinfo=datetime.timezone.utc)
    return dt


class ResolveDailyGateTest(SimpleTestCase):
    """The gate allows execution only between 04:30 and 06:00 local time."""

    def _run_task(self, hour, minute=0):
        """Patch timezone.localtime and run the task; return (ran, warned)."""
        fake_now = _make_localtime(hour, minute)
        ran = False
        warned = False

        # Patch _resolve_suplemento_ids so we can detect if the task body ran.
        def fake_suplemento():
            nonlocal ran
            ran = True
            return []

        with patch("homev4.tasks.timezone.localtime", return_value=fake_now), \
             patch("homev4.tasks._resolve_suplemento_ids", side_effect=fake_suplemento), \
             patch("homev4.tasks.HomeLayout") as mock_hl, \
             patch("homev4.tasks.logger") as mock_logger:
            mock_hl.objects.order_by.return_value.values_list.return_value.distinct.return_value = []
            from homev4.tasks import resolve_daily_layouts_task
            resolve_daily_layouts_task()
            warned = mock_logger.warning.called

        return ran, warned

    # --- inside window: task should run ---

    def test_4h30_is_allowed(self):
        ran, warned = self._run_task(4, 30)
        self.assertTrue(ran, "4:30am should be inside the window")
        self.assertFalse(warned)

    def test_4h59_is_allowed(self):
        ran, warned = self._run_task(4, 59)
        self.assertTrue(ran)
        self.assertFalse(warned)

    def test_5h00_is_allowed(self):
        ran, warned = self._run_task(5, 0)
        self.assertTrue(ran)
        self.assertFalse(warned)

    def test_5h30_is_allowed(self):
        ran, warned = self._run_task(5, 30)
        self.assertTrue(ran)
        self.assertFalse(warned)

    def test_5h59_is_allowed(self):
        ran, warned = self._run_task(5, 59)
        self.assertTrue(ran)
        self.assertFalse(warned)

    def test_6h00_is_allowed(self):
        ran, warned = self._run_task(6, 0)
        self.assertTrue(ran)
        self.assertFalse(warned)

    # --- outside window: task should be skipped with warning ---

    def test_3h04_is_blocked(self):
        """Replicates the exact early-fire incident from 2026-05-18."""
        ran, warned = self._run_task(3, 4)
        self.assertFalse(ran, "3:04am must be blocked by the gate")
        self.assertTrue(warned)

    def test_midnight_is_blocked(self):
        ran, warned = self._run_task(0, 0)
        self.assertFalse(ran)
        self.assertTrue(warned)

    def test_4h29_is_blocked(self):
        ran, warned = self._run_task(4, 29)
        self.assertFalse(ran, "4:29am is just before the window opens")
        self.assertTrue(warned)

    def test_6h01_is_blocked(self):
        ran, warned = self._run_task(6, 1)
        self.assertFalse(ran, "6:01am is just after the window closes")
        self.assertTrue(warned)

    def test_noon_is_blocked(self):
        ran, warned = self._run_task(12, 0)
        self.assertFalse(ran)
        self.assertTrue(warned)

    def test_23h59_is_blocked(self):
        ran, warned = self._run_task(23, 59)
        self.assertFalse(ran)
        self.assertTrue(warned)
