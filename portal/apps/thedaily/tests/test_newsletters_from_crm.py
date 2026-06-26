# coding:utf-8
"""
Inbound tests for the CRM-facing newsletter read/delta endpoints (usuarios/api/newsletters/ and
usuarios/api/newsletter_update/). They exercise the API key auth, the two newsletter types and, above all,
that the delta is non-destructive (never wipes the other newsletters).
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from rest_framework_api_key.models import APIKey

from core.models import Publication, Category
from thedaily.models import Subscriber

READ_URL = "/usuarios/api/newsletters/"
UPDATE_URL = "/usuarios/api/newsletter_update/"


class NewslettersFromCrmTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        _, key = APIKey.objects.create_key(name="test-nl")
        self.auth = {"HTTP_AUTHORIZATION": "Api-Key " + key}

        self.user = User.objects.create_user(
            username="nltest@example.com", email="nltest@example.com", password="x"
        )
        self.subscriber = Subscriber.objects.get_or_create(user=self.user)[0]
        self.subscriber.contact_id = 99999
        self.subscriber.save()

        self.semanal = Publication.objects.create(
            name="Semanal", slug="semanal", headline="Semanal", has_newsletter=True
        )
        self.tarde = Publication.objects.create(name="Tarde", slug="tarde", headline="Tarde", has_newsletter=True)
        self.salto = Category.objects.create(name="Salto", slug="salto", has_newsletter=True)

        self.subscriber.newsletters.add(self.semanal)
        self.subscriber.category_newsletters.add(self.salto)

    def test_read_requires_api_key(self):
        resp = self.client.post(READ_URL, {"contact_id": 99999})
        # 401 when ENV_HTTP_BASIC_AUTH is on, 403 otherwise; either way it's rejected without a key.
        self.assertIn(resp.status_code, (401, 403))

    def test_read_returns_both_types_with_state(self):
        resp = self.client.post(READ_URL, {"contact_id": 99999}, **self.auth)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["exists"])
        pubs = {p["slug"]: p["subscribed"] for p in data["publication"]}
        cats = {c["slug"]: c["subscribed"] for c in data["category"]}
        self.assertTrue(pubs["semanal"])
        self.assertFalse(pubs["tarde"])
        self.assertTrue(cats["salto"])

    def test_read_unknown_contact(self):
        resp = self.client.post(READ_URL, {"contact_id": 12345678}, **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["exists"])

    def test_delta_subscribe_is_non_destructive(self):
        # subscribe to "tarde" must NOT drop "semanal"
        resp = self.client.post(
            UPDATE_URL,
            {"contact_id": 99999, "nl_type": "publication", "slug": "tarde", "action": "subscribe"},
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["subscribed"])
        slugs = set(self.subscriber.newsletters.values_list("slug", flat=True))
        self.assertEqual(slugs, {"semanal", "tarde"})

    def test_delta_unsubscribe_only_target(self):
        resp = self.client.post(
            UPDATE_URL,
            {"contact_id": 99999, "nl_type": "publication", "slug": "semanal", "action": "unsubscribe"},
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["subscribed"])
        self.assertEqual(self.subscriber.newsletters.count(), 0)
        # category newsletter untouched
        self.assertEqual(self.subscriber.category_newsletters.count(), 1)

    def test_delta_category_type(self):
        resp = self.client.post(
            UPDATE_URL,
            {"contact_id": 99999, "nl_type": "category", "slug": "salto", "action": "unsubscribe"},
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.subscriber.category_newsletters.count(), 0)

    def test_delta_unknown_contact_404(self):
        resp = self.client.post(
            UPDATE_URL,
            {"contact_id": 12345678, "nl_type": "publication", "slug": "tarde", "action": "subscribe"},
            **self.auth,
        )
        self.assertEqual(resp.status_code, 404)
