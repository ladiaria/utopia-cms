# coding:utf-8

from builtins import range
import string
import random
import requests

from django.conf import settings
from django.test import TestCase, override_settings
from django.contrib.auth.models import User


def rand_chars(length=9):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


class CRMSyncTestCase(TestCase):

    test_user = None

    def tearDown(self):
        # Clean up test data in the CRM
        if self.test_user:
            api_url = settings.CRM_API_UPDATE_USER_URI
            api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
            if api_url and api_key:
                requests.delete(
                    api_url,
                    headers={'Authorization': 'Api-Key ' + api_key},
                    data={"email": self.test_user.email},
                )

    def test_create_user_sync(self):
        with override_settings(CRM_UPDATE_USER_ENABLED=True):
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
