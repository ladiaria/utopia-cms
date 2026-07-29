# coding:utf-8
"""
Tests for how the CRM->CMS sync API view (update_user_from_crm) resolves the site account of a
contact. It had the same narrow lookup as the update_subscribers command (User.email only), so
fixing only one of the two channels would have left the other one broken.

The two shapes below were found in production on 2026-07-29 and must be treated differently:
one is the same person and must be linked, the other is somebody else's account and must not.
"""
import json

from social_django.models import UserSocialAuth

from django.test import TestCase, override_settings
from django.test.client import Client
from django.contrib.auth.models import User

from thedaily.models import Subscriber


# example.com has no MX record, and saving a user would otherwise push it back to the CRM over HTTP
@override_settings(THEDAILY_VALIDATE_EMAIL_CHECK_MX=False, CRM_UPDATE_USER_ENABLED=False)
class UpdateUserFromCrmLinkingTestCase(TestCase):

    fixtures = ["api_key"]

    def setUp(self):
        # same key as the api_key fixture used by the other API tests
        self.client_api = Client(HTTP_AUTHORIZATION="Api-Key 8YyhdThC.3MwN8JTL1xejITadK0Sz85oBCbmWoAzK")

    def _post(self, contact_id, email, name="Test"):
        return self.client_api.post(
            "/usuarios/fromcrm",
            {"contact_id": contact_id, "email": email, "name": name, "fields": json.dumps({})},
        )

    def test_links_account_found_by_username(self):
        """Production contact 701050: address in `username`, empty `email` field."""
        user = User.objects.create_user("lyaques@example.com", "")

        self._post(900001, "lyaques@example.com")

        user.subscriber.refresh_from_db()
        self.assertEqual(user.subscriber.contact_id, 900001)

    def test_does_not_link_google_login_of_another_account(self):
        """
        Production contacts 708642 and 726884: the address is the Google login of an account that
        belongs to a different person and is already linked to that person's own CRM contact.
        Linking it would grant this contact's subscription to somebody else.
        """
        somebody_else = User.objects.create_user("ana@example.com", "ana@example.com")
        somebody_else.subscriber.contact_id = 900500
        somebody_else.subscriber.save()
        UserSocialAuth.objects.create(
            user=somebody_else, provider="google-oauth2", uid="carlos@example.com"
        )

        self._post(900002, "carlos@example.com", name="Carlos")

        somebody_else.subscriber.refresh_from_db()
        self.assertEqual(somebody_else.subscriber.contact_id, 900500)
        self.assertFalse(Subscriber.objects.filter(contact_id=900002).exists())
