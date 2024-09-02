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

    def test_sync(self):
        name, email_pre_prefix, password = "John Doe", "cms_test_crmsync_", User.objects.make_random_password()
        email = "%s%s@%s" % (email_pre_prefix, rand_chars(), settings.SITE_DOMAIN)
        # create a user with very low collission probability on email field
        user = User.objects.create_user(email, email, password)
        user.name, user.is_active = name, True
        user.save()
        self.assertIsNotNone(user.subscriber)
        user.subscriber.save()
        # insert a contact in CRM with the same data
        api_url = settings.CRM_API_UPDATE_USER_URI
        api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
        if api_url and api_key:
            requests.post(
                api_url,
                headers={'Authorization': 'Api-Key ' + api_key},
                data={"name": name, "email": email},
            )
        # change email
        new_email_prefix = "%s%s@" % (email_pre_prefix, rand_chars())
        user.email = new_email_prefix + settings.SITE_DOMAIN
        user.save()
        # check changed also in CRM (TODO: API used here is not yet opensourced in CRM, it will be ASAP)
        api_url = getattr(settings, "CRM_CONTACT_BY_EMAILPREFIX_API_URI", None)
        api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
        if api_url and api_key:
            try:
                self.assertEqual(
                    requests.post(
                        api_url,
                        headers={'Authorization': 'Api-Key ' + api_key},
                        data={"email_prefix": new_email_prefix},
                    ).json().get("email"),
                    user.email,
                )
            except Exception as exc:
                self.fail(exc)
        else:
            print("WARNING: 'CRM Contact by emailprefix' API uri not set, test full validity can't be determined")

    def test_create_user_sync(self):
        with override_settings(CRM_UPDATE_USER_ENABLED=True):
            name, email_pre_prefix, password = "Jane Doe", "cms_test_crmsync_", User.objects.make_random_password()
            email = "%s%s@%s" % (email_pre_prefix, rand_chars(), settings.SITE_DOMAIN)
            # create a user with very low collission probability on email field
            test_user = User.objects.create_user(email, email, password)
            test_user.name, test_user.is_active = name, True
            test_user.save()
            self.assertIsNotNone(test_user.subscriber)
            test_user.subscriber.save()
            print("Contact ID in CRM", test_user.subscriber.contact_id)
            # update the contact in CRM with the same data
            api_url = settings.CRM_API_UPDATE_USER_URI
            api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
            if api_url and api_key:
                res = requests.put(
                    api_url,
                    headers={'Authorization': 'Api-Key ' + api_key},
                    data={"name": name, "email": email},
                )
                self.assertEqual(res.json()["contact_id"], test_user.subscriber.contact_id)

    def test_not_create_user_sync(self):
        with override_settings(CRM_UPDATE_USER_ENABLED=False):
            name, email_pre_prefix, password = "Jane Doe", "cms_test_crmsync_", User.objects.make_random_password()
            email = "%s%s@%s" % (email_pre_prefix, rand_chars(), settings.SITE_DOMAIN)
            # create a user with very low collission probability on email field
            test_user = User.objects.create_user(email, email, password)
            test_user.name, test_user.is_active = name, True
            test_user.save()
            # get the contact in CRM with the same data
            api_url = settings.CRM_API_GET_USER_URI
            api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
            if api_url and api_key:
                res = requests.get(
                    api_url,
                    headers={'Authorization': 'Api-Key ' + api_key},
                    params={"email": email},
                )
            print(res.json()["exists"])
            self.assertFalse(res.json()["exists"])
