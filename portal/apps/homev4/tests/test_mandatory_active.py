"""
Unit tests for mandatory-active components in the layout editor.

lo_mas_leido (a read-only ranking) and recomendadas_lv (a fixed editorial slot) cannot be
deactivated. The editor renders their checkbox disabled, and save_grid enforces active=True
server-side so a crafted POST cannot turn them off.

All DB calls are mocked — no database required. Tests run with SimpleTestCase.
"""
import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from homev4.views import _MANDATORY_ACTIVE_COMP_KEYS, save_grid


def _save(componentes):
    """POST to save_grid with the given componentes list; return (response, saved_layout)."""
    factory = RequestFactory()
    body = json.dumps({"grid_data": {"componentes": componentes}})
    request = factory.post("/homev4/save-grid/1/", data=body, content_type="application/json")
    request.user = MagicMock()
    request.session = {}

    mock_layout = MagicMock()
    mock_layout.grid_data = {}

    with patch("homev4.views.get_object_or_404", return_value=mock_layout), \
         patch("homev4.views.transaction"), \
         patch("homev4.views._propagate_article_ids"), \
         patch("homev4.views._write_audit_log"), \
         patch("homev4.views._sync_principal_to_edition"), \
         patch("homev4.views._grid_stats", return_value={
             "principal": 0, "suplemento": 0,
             "sections_active": 0, "sections_total": 0, "componentes_active": [],
         }):
        response = save_grid(request, layout_id=1)
    return response, mock_layout


def _active_of(layout, key):
    """Return the saved 'active' flag for the component with the given key."""
    comp = next(c for c in layout.grid_data["componentes"] if c["key"] == key)
    return comp.get("active")


class MandatoryActiveKeysTest(SimpleTestCase):

    def test_lo_mas_leido_is_mandatory(self):
        self.assertIn("lo_mas_leido", _MANDATORY_ACTIVE_COMP_KEYS)

    def test_recomendadas_lv_is_mandatory(self):
        self.assertIn("recomendadas_lv", _MANDATORY_ACTIVE_COMP_KEYS)

    def test_opinion_is_not_mandatory(self):
        # A regular toggleable component must not be forced active.
        self.assertNotIn("opinion", _MANDATORY_ACTIVE_COMP_KEYS)


class SaveGridMandatoryActiveTest(SimpleTestCase):

    def test_lo_mas_leido_forced_active_when_posted_inactive(self):
        """A POST with lo_mas_leido active=False must be normalized to active=True."""
        response, layout = _save([{"key": "lo_mas_leido", "active": False, "article_ids": []}])
        self.assertEqual(response.status_code, 200)
        self.assertIs(_active_of(layout, "lo_mas_leido"), True)

    def test_recomendadas_lv_forced_active_when_posted_inactive(self):
        """A POST with recomendadas_lv active=False must be normalized to active=True."""
        response, layout = _save([{"key": "recomendadas_lv", "active": False, "article_ids": []}])
        self.assertEqual(response.status_code, 200)
        self.assertIs(_active_of(layout, "recomendadas_lv"), True)

    def test_regular_component_inactive_state_preserved(self):
        """A non-mandatory component keeps the active=False it was posted with."""
        response, layout = _save([{"key": "opinion", "active": False, "article_ids": []}])
        self.assertEqual(response.status_code, 200)
        self.assertIs(_active_of(layout, "opinion"), False)

    def test_mandatory_already_active_stays_active(self):
        """active=True posted for a mandatory component stays True (no regression)."""
        response, layout = _save([{"key": "lo_mas_leido", "active": True, "article_ids": []}])
        self.assertEqual(response.status_code, 200)
        self.assertIs(_active_of(layout, "lo_mas_leido"), True)
