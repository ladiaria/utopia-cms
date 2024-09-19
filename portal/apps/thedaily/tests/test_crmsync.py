# coding:utf-8
from builtins import range
import string
import random
import unittest
import requests

from django.conf import settings
from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from libs.utils import crm_rest_api_kwargs


def rand_chars(length=9):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


class CRMSyncTestCase(TestCase):

    test_user = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.are_tests_enabled():
            print("WARNING: CRM sync tests are disabled due to missing configuration.")
            raise unittest.SkipTest("CRM sync tests are disabled.")

    @staticmethod
    def are_tests_enabled():
        # Check if the necessary settings are available
        return (
            hasattr(settings, 'CRM_API_UPDATE_USER_URI') and
            hasattr(settings, 'CRM_UPDATE_USER_API_KEY') and
            settings.CRM_API_UPDATE_USER_URI and
            settings.CRM_UPDATE_USER_API_KEY
        )

    def test_sync(self):
        # (commented next line before a big merge, may reduce conflict ammount) TODO: enable after merge
        # with override_settings(CRM_UPDATE_USER_ENABLED=True, CRM_UPDATE_SUBSCRIBER_FIELDS={"allow_promotions": "allow_promotions"}):  # noqa
        name, email_pre_prefix, password = "John Doe", "cms_test_crmsync_", User.objects.make_random_password()
        email = "%s%s@%s" % (email_pre_prefix, rand_chars(), settings.SITE_DOMAIN)
        # create a user with very low collission probability on email field
        user = User.objects.create_user(email, email, password)
        user.name, user.is_active = name, True
        user.save()
        self.assertIsNotNone(user.subscriber)
        user.subscriber.save()
        # insert a contact in CRM with the same data
        api_uri = settings.CRM_API_UPDATE_USER_URI
        api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
        if api_uri and api_key:
            requests.post(api_uri, **crm_rest_api_kwargs(api_key, data={"name": name, "email": email}))
        # change email
        new_email_prefix = "%s%s@" % (email_pre_prefix, rand_chars())
        user.email = new_email_prefix + settings.SITE_DOMAIN
        user.save()
        # check changed also in CRM
        api_uri = getattr(settings, "CRM_CONTACT_BY_EMAILPREFIX_API_URI", None)
        api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
        if api_uri and api_key:
            try:
                self.assertEqual(
                    requests.post(
                        api_uri, **crm_rest_api_kwargs(api_key, data={"email_prefix": new_email_prefix})
                    ).json().get("email"),
                    user.email,
                )
            except Exception as exc:
                self.fail(exc)
        else:
            print("WARNING: 'CRM Contact by emailprefix' API uri not set, test full validity can't be determined")

        # Test changing allow_promotions field
        user.subscriber.refresh_from_db()
        user.subscriber.allow_promotions = not user.subscriber.allow_promotions
        user.subscriber.save()

        # TODO: Check if the change is reflected in CRM (uncomment when endpoint is ready)
        #       (endpoint can return something to alert if the field is not configured to be synced)
        """
        response = requests.get(
            api_url,
            headers={'Authorization': 'Api-Key ' + api_key},
            params={"email": user.email},
        )
        crm_data = response.json()

        self.assertEqual(
            crm_data.get("allow_promotions"),
            user.subscriber.allow_promotions,
            "allow_promotions field in CRM does not match the updated value"
        )
        """

    def test_create_user_sync(self):
        with override_settings(CRM_UPDATE_USER_ENABLED=True, CRM_UPDATE_USER_CREATE_CONTACT=True):
            name, email_pre_prefix, password = "Jane Doe", "cms_test_crmsync_", User.objects.make_random_password()
            email = "%s%s@%s" % (email_pre_prefix, rand_chars(), settings.SITE_DOMAIN)
            # create a user with very low collission probability on email field
            self.test_user = User.objects.create_user(email, email, password)
            self.test_user.name, self.test_user.is_active = name, True
            self.test_user.save()
            self.assertIsNotNone(self.test_user.subscriber)
            self.test_user.subscriber.save()
            # update the contact in CRM with the same data
            api_url = settings.CRM_API_UPDATE_USER_URI
            api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
            if api_url and api_key:
                res = requests.put(
                    api_url,
                    headers={'Authorization': 'Api-Key ' + api_key},
                    data={"name": name, "email": email},
                )
                self.assertEqual(res.json()["contact_id"], self.test_user.subscriber.contact_id)

    def test_delete_user_sync(self):
        # Clean up test data in the CRM
        # TODO: this does not tests any "sync" feature, only tests that the api call works ok (rename or fix)
        if self.test_user:
            api_url = settings.CRM_API_UPDATE_USER_URI
            api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
            if api_url and api_key:
                res = requests.delete(
                    api_url,
                    headers={'Authorization': 'Api-Key ' + api_key},
                    data={"email": self.test_user.email},
                )

                # check if user exists in the CRM
                api_url = settings.CRM_API_GET_USER_URI
                api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
                if api_url and api_key:
                    res = requests.get(
                        api_url,
                        headers={'Authorization': 'Api-Key ' + api_key},
                        params={"email": self.test_user.email},
                    )
                self.assertFalse(res.json()["exists"])

    def test_not_create_user_without_sync(self):
        with override_settings(CRM_UPDATE_USER_ENABLED=False):
            name, email_pre_prefix, password = "Jane Doe", "cms_test_crmsync_", User.objects.make_random_password()
            email = "%s%s@%s" % (email_pre_prefix, rand_chars(), settings.SITE_DOMAIN)
            # create a user with very low collission probability on email field
            no_sync_user = User.objects.create_user(email, email, password)
            no_sync_user.name, no_sync_user.is_active = name, True
            no_sync_user.save()
            # get the contact in CRM with the same data
            api_url = settings.CRM_API_GET_USER_URI
            api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
            if api_url and api_key:
                res = requests.get(
                    api_url,
                    headers={'Authorization': 'Api-Key ' + api_key},
                    params={"email": email},
                )

            self.assertFalse(res.json()["exists"])
