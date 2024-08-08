# coding:utf-8
from django.conf import settings
from django.test import TestCase, Client

from core.models import Section, Category


class CategoryTestCase(TestCase):

    fixtures = ['test']

    def test01_section_inclusion_in_menu(self):
        a1 = Category.objects.get(id=1)
        s4 = Section.objects.get(id=4)
        c = Client()
        res = c.get(f'/{a1.slug}/', {}, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(res.status_code, 200)
        a_target = f'<a class="section-detail__header-sub-cat" href="{s4.get_absolute_url()}"'
        self.assertIn(a_target, res.content.decode())
        s4.included_in_category_menu = False
        s4.save()
        res = c.get(f'/{a1.slug}/', {}, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(a_target, res.content.decode())
