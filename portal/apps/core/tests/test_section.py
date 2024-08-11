# coding:utf-8
from django.conf import settings
from django.test import TestCase, Client

from core.models import Section


class SectionTestCase(TestCase):

    fixtures = ['test']

    def test01_latest(self):
        s1 = Section.objects.get(id=1)
        # 1 - without params
        # article9 should be the first because is the one with the latest date_published
        self.assertEqual(s1.latest()[0].id, 9)

    def test02_section_back_publication(self):
        with self.settings(CORE_SECTION_MAIN_PUBLICATION={'spinoff': ['news']}):
            s1 = Section.objects.get(id=1)
            c = Client()
            res = c.get('/seccion/{}/'.format(s1.slug), {}, HTTP_HOST=settings.SITE_DOMAIN)
            self.assertEqual(res.status_code, 200)
            # test the go back link href with the publication slug is present in the view
            self.assertRegex(res.content.decode(), r'<a class=".*" href="/spinoff/">')
