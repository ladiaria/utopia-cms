from django.test import TestCase

from core.factories import PublicationFactory
from homev4.models import HomeLayout


class HomeV4DummyTest(TestCase):

    def test_dummy(self):
        pub = PublicationFactory()
        layout = HomeLayout.objects.create(name="Test layout", publication=pub)
        self.assertEqual(HomeLayout.objects.filter(pk=layout.pk).count(), 1)
