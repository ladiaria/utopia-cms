# -*- coding: utf-8 -*-
from django.conf import settings
from django.test import TestCase, Client

from core.models import Journalist


class BaseJournalistTestCase(TestCase):

    fixtures = ['test']

    def setUp(self):
        self.client = Client()
        self.journalist = Journalist.objects.get(slug="test-journalist")
        self.journalist_other_job = Journalist.objects.get(slug="test-columnist")
        self.journalist_wnumber_in_name = Journalist.objects.create(
            name="Jonh 123 Doe",
            slug="john-123-doe",
            job="PE",
            bio="Journalist bio for test purpouses",
            ig="https://www.instagram.com/john123doe",
        )


class JournalistTestCase(BaseJournalistTestCase):

    def test01_social_instagram_info(self):
        journalist_url = self.journalist.get_absolute_url()
        response = self.client.get(journalist_url, follow=True, HTTP_HOST=settings.SITE_DOMAIN)
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
            response = self.client.get(journalist_url, follow=True, HTTP_HOST=settings.SITE_DOMAIN)
            content = response.content.decode()
            splitted1, splitted2 = content.split(target_string)
            self.assertIn(bs_verbose_name, splitted2.lower())
            self.assertNotIn(bs_verbose_name, splitted1.lower())
            self.assertNotIn(target_string, splitted1)
            self.assertNotIn(target_string, splitted2)

    def test02_url_unchanged(self):
        # is periodista
        slug = self.journalist.slug
        response = self.client.get(self.journalist.get_absolute_url(), follow=True, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], f'/periodista/{slug}/')

        # columnista -> periodista
        response = self.client.get(f"/columnista/{slug}/", follow=True, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], f'/periodista/{slug}/')

        # other not found
        for other in ['autor', 'author']:
            response = self.client.get(f"/{other}/{slug}/", follow=True, HTTP_HOST=settings.SITE_DOMAIN)
            self.assertEqual(response.status_code, 404)

        # is columnista
        slug = self.journalist_other_job.slug
        response = self.client.get(self.journalist_other_job.get_absolute_url(), HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], f'/columnista/{slug}/')

        # periodista -> columnista
        response = self.client.get(f"/periodista/{slug}/", follow=True, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], f'/columnista/{slug}/')

        # other not found
        for other in ['autor', 'author']:
            response = self.client.get(f"/{other}/{slug}/", follow=True, HTTP_HOST=settings.SITE_DOMAIN)
            self.assertEqual(response.status_code, 404)

        # number in name is ok
        response = self.client.get(
            self.journalist_wnumber_in_name.get_absolute_url(), follow=True, HTTP_HOST=settings.SITE_DOMAIN
        )
        self.assertEqual(response.status_code, 200)
