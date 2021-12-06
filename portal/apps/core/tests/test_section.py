# coding:utf8
from django.test import TestCase

from core.models import Section


class SectionTestCase(TestCase):

    fixtures = ['test']

    def test_latest(self):
        s1 = Section.objects.get(id=1)
        # 1 - without params
        # article3 should be the first because is the one with the latest date_published
        self.assertEqual(s1.latest()[0].id, 3)
