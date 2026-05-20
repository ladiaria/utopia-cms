"""
Unit tests for custom_500_handler().

The handler wraps render() in a try/except so that if the 500 template
itself raises (e.g. a context processor calls markdown2 on broken HTML),
uwsgi can still send a valid HTTP response instead of crashing with
0 headers — which Cloudflare turns into a 502.

Contract under test:
- Happy path      → render() result is returned unchanged.
- Fallback path   → any Exception from render() produces an HttpResponse
                    with status 500, HTML content-type, and content that
                    mirrors the real 500 template (CSS, logo, error text,
                    home link).
"""
from unittest.mock import MagicMock, patch

from django.http import HttpResponse
from django.test import SimpleTestCase, override_settings

from homev3.views import custom_500_handler


def _make_request():
    return MagicMock()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class Custom500HandlerHappyPathTest(SimpleTestCase):
    """When render() succeeds, its result is returned as-is."""

    def test_returns_render_result_on_success(self):
        """The response from render() is forwarded directly to the caller."""
        expected = MagicMock()
        with patch("homev3.views.render", return_value=expected), \
             patch("homev3.views.settings") as mock_settings:
            mock_settings.HOMEV3_LOGO = "img/logo.svg"
            mock_settings.HOMEV3_500_TEMPLATE = "500.html"
            result = custom_500_handler(_make_request())
        self.assertIs(result, expected)

    def test_render_called_with_500_status(self):
        """render() is always invoked with status=500."""
        with patch("homev3.views.render", return_value=MagicMock()) as mock_render, \
             patch("homev3.views.settings") as mock_settings:
            mock_settings.HOMEV3_LOGO = "img/logo.svg"
            mock_settings.HOMEV3_500_TEMPLATE = "500.html"
            custom_500_handler(_make_request())
        _, kwargs = mock_render.call_args
        self.assertEqual(kwargs.get("status"), 500)


# ---------------------------------------------------------------------------
# Fallback path — triggered by any Exception from render()
# ---------------------------------------------------------------------------

class Custom500HandlerFallbackTest(SimpleTestCase):
    """When render() raises, the fallback inline HTML response is returned."""

    _STATIC_URL = "/static/"
    _LOGO = "img/logo.png"

    def _run_fallback(self, exc=None):
        """Simulate render() raising exc (defaults to a generic Exception)."""
        if exc is None:
            exc = Exception("template crash")
        with patch("homev3.views.render", side_effect=exc), \
             override_settings(STATIC_URL=self._STATIC_URL, HOMEV3_LOGO=self._LOGO):
            return custom_500_handler(_make_request())

    def test_fallback_returns_http_response(self):
        """The fallback is an HttpResponse instance."""
        self.assertIsInstance(self._run_fallback(), HttpResponse)

    def test_fallback_status_is_500(self):
        """The fallback response has HTTP status 500."""
        self.assertEqual(self._run_fallback().status_code, 500)

    def test_fallback_content_type_is_html(self):
        """The fallback response is text/html with utf-8 charset."""
        ct = self._run_fallback()["Content-Type"]
        self.assertIn("text/html", ct)
        self.assertIn("utf-8", ct)

    def test_fallback_contains_error_heading(self):
        """The fallback body contains the 'Error de sistema' heading."""
        self.assertIn(b"Error de sistema", self._run_fallback().content)

    def test_fallback_contains_apology_text(self):
        """The fallback body contains the user-facing apology paragraph."""
        self.assertIn(b"Ha ocurrido un error en el sistema", self._run_fallback().content)

    def test_fallback_contains_patience_text(self):
        """The fallback body contains the 'Gracias por tu paciencia' paragraph."""
        self.assertIn(b"Gracias por tu paciencia", self._run_fallback().content)

    def test_fallback_contains_home_link(self):
        """The fallback body contains a link to the home page."""
        self.assertIn(b'href="/"', self._run_fallback().content)

    def test_fallback_contains_logo(self):
        """The fallback body includes the logo via STATIC_URL + HOMEV3_LOGO."""
        expected = (self._STATIC_URL + self._LOGO).encode()
        self.assertIn(expected, self._run_fallback().content)

    def test_fallback_contains_base_css(self):
        """The fallback body links to the admin base.css stylesheet."""
        self.assertIn(b"admin/css/base.css", self._run_fallback().content)

    def test_fallback_contains_login_css(self):
        """The fallback body links to the admin login.css stylesheet."""
        self.assertIn(b"admin/css/login.css", self._run_fallback().content)

    def test_fallback_triggered_by_assertion_error(self):
        """AssertionError (the real production failure mode) is caught."""
        self.assertEqual(self._run_fallback(exc=AssertionError("markdown2 bug")).status_code, 500)

    def test_fallback_triggered_by_template_does_not_exist(self):
        """TemplateDoesNotExist is also caught by the broad except clause."""
        from django.template.exceptions import TemplateDoesNotExist
        self.assertEqual(self._run_fallback(exc=TemplateDoesNotExist("500.html")).status_code, 500)
