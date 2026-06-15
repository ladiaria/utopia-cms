"""
Unit tests for the Radio Mundial guard in toggle_radio_block_task.

Background:
  The scheduled task turns the regular "radio" block on (7am) and off (10pm) in every
  home layout. Radio and Radio Mundial share the same sidebar slot and are mutually
  exclusive (enforced in the layout editor by _validate_radio_exclusivity). The cron
  writes directly to the layouts, bypassing that editor validation, so without a guard
  the 7am turn-on would set "radio" active in layouts where "radio_mundial" is already
  active — leaving both blocks on, a state the editor never allows.

  These tests pin the guard's behavior:
    - activating (active=True) must SKIP layouts where radio_mundial is active,
    - deactivating (active=False) has NO guard (turning radio off is always safe).

All tests use SimpleTestCase + mocks — no database. HomeLayout and Publication are
mocked, and utopia_cms_radio.models is stubbed so the final RadioGeneralConfig sync
never reaches the DB regardless of whether the radio app is installed in test settings.
"""

import sys
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


def _make_pub_cls(mock_instance):
    """Return a fake Publication class with a real DoesNotExist and a configured objects.get."""
    cls = MagicMock()
    cls.DoesNotExist = type("DoesNotExist", (Exception,), {})
    cls.objects.get.return_value = mock_instance
    return cls


def _layout(componentes):
    """Build a mock HomeLayout whose grid_data holds the given componentes list."""
    layout = MagicMock()
    layout.grid_data = {"componentes": componentes}
    return layout


def _radio_state(layout):
    """Return {key: active} for the radio/radio_mundial components of a layout."""
    return {
        c.get("key"): c.get("active")
        for c in layout.grid_data["componentes"]
        if c.get("key") in ("radio", "radio_mundial")
    }


class ToggleRadioBlockGuardTest(SimpleTestCase):

    def _run_toggle(self, active, layouts):
        """
        Run toggle_radio_block_task(active) against one publication that owns `layouts`.
        HomeLayout/Publication are mocked and the radio app is stubbed; the same `layouts`
        objects are returned mutated so callers can inspect their grid_data afterwards.
        """
        mock_pub = MagicMock()
        mock_pub.slug = "ladiaria"
        mock_pub_cls = _make_pub_cls(mock_pub)

        # Stub the radio app so `from utopia_cms_radio.models import RadioGeneralConfig`
        # inside the task resolves to a mock (no real import, no DB write in SimpleTestCase).
        stub_models = MagicMock()
        with patch.dict(
            sys.modules,
            {"utopia_cms_radio": MagicMock(), "utopia_cms_radio.models": stub_models},
        ), patch("homev4.tasks.HomeLayout") as mock_hl, patch(
            "core.models.Publication", new=mock_pub_cls
        ), patch("homev4.tasks.logger"):
            mock_hl.objects.order_by.return_value.values_list.return_value.distinct.return_value = [1]
            mock_hl.objects.filter.return_value = layouts

            from homev4.tasks import toggle_radio_block_task
            toggle_radio_block_task(active)

        return layouts

    def test_activate_skips_layout_with_radio_mundial_active(self):
        """7am turn-on must NOT enable radio where radio_mundial is active (no la pisa)."""
        layout = _layout([
            {"key": "radio", "active": False},
            {"key": "radio_mundial", "active": True},
        ])
        self._run_toggle(True, [layout])

        self.assertEqual(_radio_state(layout), {"radio": False, "radio_mundial": True})
        # Untouched layout must not be written back.
        layout.save.assert_not_called()

    def test_activate_turns_on_radio_when_no_radio_mundial(self):
        """With no Radio Mundial component, the turn-on enables radio normally."""
        layout = _layout([{"key": "radio", "active": False}])
        self._run_toggle(True, [layout])

        self.assertEqual(_radio_state(layout), {"radio": True})
        layout.save.assert_called_once_with(update_fields=["grid_data"])

    def test_activate_turns_on_radio_when_radio_mundial_inactive(self):
        """Radio Mundial present but inactive does not block the turn-on."""
        layout = _layout([
            {"key": "radio", "active": False},
            {"key": "radio_mundial", "active": False},
        ])
        self._run_toggle(True, [layout])

        self.assertEqual(_radio_state(layout), {"radio": True, "radio_mundial": False})
        layout.save.assert_called_once_with(update_fields=["grid_data"])

    def test_activate_treats_missing_active_flag_as_active(self):
        """
        A radio_mundial component without an explicit "active" key counts as active,
        matching _validate_radio_exclusivity's comp.get("active", True) convention, so
        the guard still skips the layout.
        """
        layout = _layout([
            {"key": "radio", "active": False},
            {"key": "radio_mundial"},  # no "active" key -> treated as active
        ])
        self._run_toggle(True, [layout])

        self.assertEqual(_radio_state(layout).get("radio"), False)
        layout.save.assert_not_called()

    def test_deactivate_turns_off_radio_even_with_radio_mundial_active(self):
        """10pm turn-off has no guard: radio is disabled regardless of Radio Mundial."""
        layout = _layout([
            {"key": "radio", "active": True},
            {"key": "radio_mundial", "active": True},
        ])
        self._run_toggle(False, [layout])

        self.assertEqual(_radio_state(layout), {"radio": False, "radio_mundial": True})
        layout.save.assert_called_once_with(update_fields=["grid_data"])

    def test_activate_mixed_layouts_only_skips_the_one_with_mundial(self):
        """Across layouts, only those with radio_mundial active are skipped; others turn on."""
        with_mundial = _layout([
            {"key": "radio", "active": False},
            {"key": "radio_mundial", "active": True},
        ])
        without_mundial = _layout([{"key": "radio", "active": False}])
        self._run_toggle(True, [with_mundial, without_mundial])

        self.assertEqual(_radio_state(with_mundial), {"radio": False, "radio_mundial": True})
        with_mundial.save.assert_not_called()

        self.assertEqual(_radio_state(without_mundial), {"radio": True})
        without_mundial.save.assert_called_once_with(update_fields=["grid_data"])
