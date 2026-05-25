"""
Unit tests for resolve_daily_layouts_task:
  1. Time-gate: prevents early firing by django_celery_beat after beat restarts.
  2. Pending sync: _sync_principal_to_edition is called after applying pending_grid_data
     so that ArticleRel home_top/top_position reflect the editor's principal order and
     celery:refresh does not drop articles that lack EN PORTADA before the 5am run.

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


class ResolveDailyPendingSyncTest(SimpleTestCase):
    """_sync_principal_to_edition is called after applying pending_grid_data at 5am."""

    def _run_pending_task(self, pending_grid_data):
        """Run the task with a mocked pending layout; return the mock_sync call args."""
        fake_now = datetime.datetime(2026, 5, 22, 5, 0, tzinfo=datetime.timezone.utc)
        fake_today = datetime.date(2026, 5, 22)

        old_grid = {"principal": {"article_ids": [10, 20, 30]}}
        mock_pending_layout = MagicMock()
        mock_pending_layout.pending_grid_data = pending_grid_data

        mock_layout = MagicMock()
        mock_layout.grid_data = old_grid

        atomic_cm = MagicMock()
        atomic_cm.__enter__ = MagicMock(return_value=None)
        atomic_cm.__exit__ = MagicMock(return_value=False)
        DoesNotExist = type("DoesNotExist", (Exception,), {})

        with patch("homev4.tasks.timezone.localtime", return_value=fake_now), \
             patch("homev4.tasks.timezone.localdate", return_value=fake_today), \
             patch("homev4.tasks._sync_principal_to_edition") as mock_sync, \
             patch("homev4.tasks._propagate_article_ids"), \
             patch("homev4.tasks._write_audit_log"), \
             patch("homev4.tasks.get_papel_url"), \
             patch("homev4.tasks.transaction.atomic", return_value=atomic_cm), \
             patch("homev4.tasks.HomeLayout") as mock_hl, \
             patch("django.core.cache.cache"), \
             patch("core.models.Publication") as mock_pub_cls:

            mock_hl.objects.order_by.return_value.values_list.return_value.distinct.return_value = [1]
            mock_hl.objects.filter.return_value.first.return_value = mock_pending_layout
            mock_hl.get_active_layout.return_value = mock_layout
            mock_pub_cls.objects.get.return_value = MagicMock(slug="ladiaria")
            mock_pub_cls.DoesNotExist = DoesNotExist

            from homev4.tasks import resolve_daily_layouts_task
            resolve_daily_layouts_task()

        return mock_sync, mock_layout

    def test_sync_called_with_principal_ids(self):
        """Applying pending_grid_data must sync home_top on ArticleRel for the new principal."""
        new_principal = [40, 10, 20]
        pending_grid = {"principal": {"article_ids": new_principal}}
        mock_sync, mock_layout = self._run_pending_task(
            {"date": "2026-05-22", "grid": pending_grid}
        )
        mock_sync.assert_called_once_with([10, 20, 30], new_principal, mock_layout, None)

    def test_sync_called_with_empty_new_principal(self):
        """Even when pending principal is empty, sync is called so stale home_top flags are cleared."""
        pending_grid = {"principal": {"article_ids": []}}
        mock_sync, mock_layout = self._run_pending_task(
            {"date": "2026-05-22", "grid": pending_grid}
        )
        mock_sync.assert_called_once_with([10, 20, 30], [], mock_layout, None)

    def test_sync_not_called_without_pending(self):
        """Without pending_grid_data the principal is not changed, so no sync needed."""
        fake_now = datetime.datetime(2026, 5, 22, 5, 0, tzinfo=datetime.timezone.utc)
        fake_today = datetime.date(2026, 5, 22)

        mock_layout = MagicMock()
        mock_layout.grid_data = {"principal": {"article_ids": [1, 2]}}

        atomic_cm = MagicMock()
        atomic_cm.__enter__ = MagicMock(return_value=None)
        atomic_cm.__exit__ = MagicMock(return_value=False)
        DoesNotExist = type("DoesNotExist", (Exception,), {})

        with patch("homev4.tasks.timezone.localtime", return_value=fake_now), \
             patch("homev4.tasks.timezone.localdate", return_value=fake_today), \
             patch("homev4.tasks._sync_principal_to_edition") as mock_sync, \
             patch("homev4.tasks._propagate_article_ids"), \
             patch("homev4.tasks._write_audit_log"), \
             patch("homev4.tasks._resolve_suplemento_ids", return_value=[]), \
             patch("homev4.tasks.get_papel_url"), \
             patch("homev4.tasks.transaction.atomic", return_value=atomic_cm), \
             patch("homev4.tasks.HomeLayout") as mock_hl, \
             patch("django.core.cache.cache"), \
             patch("core.models.Publication") as mock_pub_cls:

            mock_hl.objects.order_by.return_value.values_list.return_value.distinct.return_value = [1]
            mock_hl.objects.filter.return_value.first.return_value = None  # no pending
            mock_hl.get_active_layout.return_value = mock_layout
            mock_pub_cls.objects.get.return_value = MagicMock(slug="ladiaria")
            mock_pub_cls.DoesNotExist = DoesNotExist

            from homev4.tasks import resolve_daily_layouts_task
            resolve_daily_layouts_task()

        mock_sync.assert_not_called()
