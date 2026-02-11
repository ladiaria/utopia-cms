# coding:utf-8
from django.conf import settings
from django.test import TestCase, Client, tag
from django.urls import reverse

from core.models import Section, Category


# TODO: (say if next TODO happens here or for a custom installation of our customers)
@tag("skippable")  # TODO: we still have unsolved scenarios where line 20 fails with 404 (very hard to know why)
class CategoryTestCase(TestCase):

    fixtures = ['test']

    def test01_section_inclusion_in_menu(self):
        a1 = Category.objects.get(slug="test")
        s4 = Section.objects.get(id=4)
        c = Client()
        url = reverse("home", kwargs={"domain_slug": a1.slug})
        res = c.get(url, {}, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(res.status_code, 200)
        a_target = r'<a class=".+" href="%s"' % s4.get_absolute_url()
        self.assertRegex(res.content.decode(), a_target)
        s4.included_in_category_menu = False
        s4.save()
        res = c.get(url, {}, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(a_target, res.content.decode())
