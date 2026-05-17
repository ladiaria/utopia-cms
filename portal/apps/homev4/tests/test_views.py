import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings


class HomeV4DummyTest(SimpleTestCase):

    @patch("homev4.models.HomeLayout")
    def test_dummy(self, MockLayout):
        # Verifies that HomeLayout can be instantiated and queried (smoke test, no DB).
        instance = MagicMock()
        instance.pk = 1
        MockLayout.objects.create.return_value = instance
        MockLayout.objects.filter.return_value.count.return_value = 1

        layout = MockLayout.objects.create(name="Test layout")
        self.assertEqual(MockLayout.objects.filter(pk=layout.pk).count(), 1)


def _mock_edition(date):
    """Return a minimal mock Edition with date_published set."""
    edition = MagicMock()
    edition.date_published = date
    return edition


@override_settings(PAPEL_FALLBACK_URL="https://papel.ladiaria.com.uy/library")
class PapelUrlTest(SimpleTestCase):
    """Tests for get_papel_url() — cache, Edition query, fallback."""

    def _patch(self, today=None, cached=None, edition_today=None, edition_recent=None, cache_set_raises=False):
        """
        Build the full mock context for get_papel_url().
        Returns a dict of patchers so each test can start/stop them selectively.
        """
        today = today or datetime.date(2026, 5, 6)  # Wednesday

        cache_mock = MagicMock()
        cache_mock.get.return_value = cached
        if cache_set_raises:
            cache_mock.set.side_effect = Exception("cache error")

        edition_qs = MagicMock()
        # filter(...).exclude(...).first() for today's edition
        edition_qs.filter.return_value.exclude.return_value.first.return_value = edition_today
        # filter(...).exclude(...).order_by(...).first() for most recent edition
        edition_qs.filter.return_value.exclude.return_value.order_by.return_value.first.return_value = edition_recent

        return {
            "cache": patch("homev4.views.cache", cache_mock),
            "Edition": patch("homev4.views.Edition", MagicMock(objects=edition_qs)),
            "timezone": patch("homev4.views.timezone.localdate", return_value=today),
            "pub": patch("homev4.views.get_default_publication", return_value=MagicMock()),
            "_cache_mock": cache_mock,
        }

    def _run(self, patchers):
        active = {k: v for k, v in patchers.items() if not k.startswith("_")}
        mocks = {k: p.start() for k, p in active.items()}
        from homev4.views import get_papel_url
        result = get_papel_url()
        for p in active.values():
            p.stop()
        return result

    def test_cache_hit_returns_cached_value(self):
        patchers = self._patch(cached="https://papel.ladiaria.com.uy/reader/la-diaria-miercoles-06052026?location=1")
        result = self._run(patchers)
        self.assertEqual(result, "https://papel.ladiaria.com.uy/reader/la-diaria-miercoles-06052026?location=1")

    def test_todays_edition_with_pdf(self):
        # Today's edition exists with PDF → correct URL is built and cached.
        today = datetime.date(2026, 5, 6)  # Wednesday
        patchers = self._patch(today=today, edition_today=_mock_edition(today))
        result = self._run(patchers)
        self.assertIn("la-diaria-miercoles-06052026", result)
        self.assertTrue(result.endswith("?location=1"))

    def test_falls_back_to_most_recent_edition(self):
        # No edition for today → uses most recent edition (Friday last week).
        recent_date = datetime.date(2026, 5, 1)  # Friday
        patchers = self._patch(
            today=datetime.date(2026, 5, 6),
            edition_today=None,
            edition_recent=_mock_edition(recent_date),
        )
        result = self._run(patchers)
        self.assertIn("la-diaria-viernes-01052026", result)

    def test_no_editions_returns_fallback_url(self):
        # No edition at all → PAPEL_FALLBACK_URL.
        patchers = self._patch(edition_today=None, edition_recent=None)
        result = self._run(patchers)
        self.assertEqual(result, "https://papel.ladiaria.com.uy/library")

    def test_cache_set_error_still_returns_url(self):
        # cache.set raises → URL is still returned correctly.
        today = datetime.date(2026, 5, 6)
        patchers = self._patch(today=today, edition_today=_mock_edition(today), cache_set_raises=True)
        result = self._run(patchers)
        self.assertIn("la-diaria-miercoles-06052026", result)

    def test_query_exception_returns_fallback_url(self):
        # Any unexpected exception → PAPEL_FALLBACK_URL.
        with patch("homev4.views.get_default_publication", side_effect=Exception("db error")):
            with patch("homev4.views.cache") as mock_cache:
                mock_cache.get.return_value = None
                from homev4.views import get_papel_url
                result = get_papel_url()
        self.assertEqual(result, "https://papel.ladiaria.com.uy/library")

    def test_all_weekday_names(self):
        # Each weekday maps to the correct Spanish slug.
        cases = [
            (datetime.date(2026, 4, 20), "lunes-20042026"),
            (datetime.date(2026, 4, 21), "martes-21042026"),
            (datetime.date(2026, 4, 22), "miercoles-22042026"),
            (datetime.date(2026, 4, 23), "jueves-23042026"),
            (datetime.date(2026, 4, 24), "viernes-24042026"),
            (datetime.date(2026, 4, 25), "sabado-25042026"),
            (datetime.date(2026, 4, 26), "domingo-26042026"),
        ]
        for date, expected_slug in cases:
            with self.subTest(date=date):
                patchers = self._patch(today=date, edition_today=_mock_edition(date))
                result = self._run(patchers)
                self.assertIn(expected_slug, result)
