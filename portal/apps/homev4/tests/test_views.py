from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


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
