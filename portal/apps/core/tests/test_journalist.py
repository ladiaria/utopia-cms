# coding:utf-8
from django.conf import settings
from django.urls import reverse
from django.test import TestCase, Client
from core.models import Journalist


class JournalistTestCase(TestCase):
    def setUp(self):
        self.journalist = Journalist.objects.create(
            name="Jonh Doe",
            slug="john-doe",
            bio="Journalist bio for test purpouses",
            ig="https://www.instagram.com/johndoe",
            bs="https://www.bluesky.com/johndoe",
        )

    def test_social_instagram_info(self):
        c = Client()
        journalist_url = reverse(
            "journalist_detail", kwargs={"journalist_job": "periodista", "journalist_slug": self.journalist.slug}
        )
        response = c.get(journalist_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 200)
        ig_verbose_name = str(self.journalist._meta.get_field('ig').verbose_name)
        target_string = "<title>Seguir en {}</title>".format(ig_verbose_name.capitalize())
        content = response.content.decode()
        self.assertIn(target_string, content)
        # by default, bluesky is rendered before instagram:
        splitted1, splitted2 = content.split(target_string)
        bs_verbose_name = str(self.journalist._meta.get_field('bs').verbose_name)
        self.assertIn(bs_verbose_name, splitted1.lower())
        self.assertNotIn(bs_verbose_name, splitted2.lower())
        self.assertNotIn(target_string, splitted1)
        self.assertNotIn(target_string, splitted2)
        # now, if a custom order is set, bluesky should be rendered after instagram:
        with self.settings(CORE_JOURNALIST_SOCIAL_ORDER=['instagram', 'bluesky']):
            response = c.get(journalist_url, HTTP_HOST=settings.SITE_DOMAIN)
            content = response.content.decode()
            splitted1, splitted2 = content.split(target_string)
            self.assertIn(bs_verbose_name, splitted2.lower())
            self.assertNotIn(bs_verbose_name, splitted1.lower())
            self.assertNotIn(target_string, splitted1)
            self.assertNotIn(target_string, splitted2)
