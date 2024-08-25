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
            ig="https://www.instagram.com/johndoe"
        )

    def test_social_instagram_info(self):
        c = Client()
        # journalist_url = f"/PE/{self.journalist.slug}"  # to be redirected to the non-accent version (í->i)
        journalist_url = reverse("journalist_detail", kwargs={
            "journalist_job": "periodista", "journalist_slug": self.journalist.slug})
        response = c.get(journalist_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 200)
        verbose_name = str(self.journalist._meta.get_field('ig').verbose_name)
        target_string = "<title>Seguir en {}</title>".format(verbose_name.capitalize())
        self.assertIn(target_string, response.content.decode())
