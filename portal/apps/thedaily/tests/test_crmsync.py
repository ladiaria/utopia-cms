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
from thedaily.models import createcrmuser, existscrmuser


def rand_chars(length=9):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


class CRMSyncTestCase(TestCase):

    api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
    test_user = None
    email_pre_prefix = "cms_test_crmsync_"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if settings.CRM_API_UPDATE_USER_URI and cls.api_key:
            name, password = "John Doe", User.objects.make_random_password()
            email = "%s%s@%s" % (cls.email_pre_prefix, rand_chars(), "gmail.com")
            # create a user with very low collission probability on email field
            cls.test_user = User.objects.create_user(email, email, password)
            cls.test_user.name, cls.test_user.is_active = name, True
            cls.test_user.save()
            if not settings.CRM_UPDATE_USER_CREATE_CONTACT:
                createcrmuser(cls.test_user.name, cls.test_user.email)
        else:
            print("WARNING: CRM sync tests are disabled due to missing configuration.")
            raise unittest.SkipTest("CRM sync tests are disabled.")

    def tearDown(cls):
        # Clean up test data here (if any) and this will cause the same removal in the CRM
        if cls.test_user.id:
            cls.test_user.delete()
        super().tearDown()

    def test1_sync(self):
        # start with a contact in the CRM
        api_uri = settings.CRM_API_GET_USER_URI
        if api_uri:
            self.assertTrue(existscrmuser(self.test_user.email).get("exists"))
        else:
            print("WARNING: 'CRM getuser API uri not set, test full validity can't be determined")
        # change email
        self.test_user.email = "%s%s@%s" % (self.email_pre_prefix, rand_chars(), "gmail.com")
        self.test_user.save()
        # check changed also in CRM
        api_uri = settings.CRM_API_GET_USER_URI
        if api_uri:
            self.test_user.refresh_from_db()
            self.assertTrue(existscrmuser(self.test_user.email).get("exists"))
        else:
            print("WARNING: 'CRM getuser API uri not set, test full validity can't be determined")

        # Test changing allow_promotions field
        self.test_user.subscriber.refresh_from_db()
        self.test_user.subscriber.allow_promotions = not self.test_user.subscriber.allow_promotions
        self.test_user.subscriber.save()

        # TODO: Check if the change is reflected in CRM (uncomment and update using new "**" way when endpoint ready)
        #       (endpoint can return something to alert if the field is not configured to be synced)
        #       (any endpoint that returns the contact data can be used, to check if the field was synced)
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

    def test2_call_update_api(self):
        api_uri = settings.CRM_API_UPDATE_USER_URI
        res = requests.put(
            api_uri,
            **crm_rest_api_kwargs(
                self.api_key, data={"name": self.test_user.first_name, "email": self.test_user.email}
            ),
        ).json()
        c_id = res.get("contact_id")
        self.assertTrue(c_id)
        # TODO: check if the else part of next if got broken by new sync approach
        if settings.CRM_UPDATE_USER_CREATE_CONTACT:
            # TODO: failing, the explanation of this assert is that this class setUp method creates the user and the
            #       signal related will create the peer contact in CRM, this signal also sets the contact_id in the
            #       subscriber model? (check/fix if this is/must happen first). Then the assert here will pass.
            self.assertEqual(res.get("contact_id"), self.test_user.subscriber.contact_id)

    def test3_delete_user_sync(self):
        if not self.test_user.id:
            self.setUpClass()
        self.assertIsNotNone(self.test_user.id)
        self.test_user.delete()
        if settings.CRM_UPDATE_USER_CREATE_CONTACT:
            api_uri = settings.CRM_API_GET_USER_URI
            if api_uri:
                pass
                # TODO: uncoment when deletion sync is implemented
                # self.assertFalse(
                #     requests.get(
                #        api_uri + "?email=" + self.test_user.email, **crm_rest_api_kwargs(self.api_key)
                #    ).json().get("exists"),
                # )

    def test4_not_create_user_without_sync(self):
        with override_settings(CRM_UPDATE_USER_CREATE_CONTACT=False):
            name, email_pre_prefix, password = "Jane Doe", "cms_test_crmsync_", User.objects.make_random_password()
            email = "%s%s@%s" % (email_pre_prefix, rand_chars(), "gmail.com")
            # create a user with very low collission probability on email field
            no_sync_user = User.objects.create_user(email, email, password)
            no_sync_user.name, no_sync_user.is_active = name, True
            no_sync_user.save()
            # get the contact in CRM with the same data
            api_uri = settings.CRM_API_GET_USER_URI
            if api_uri:
                self.assertEqual(existscrmuser(no_sync_user.email).get("exists"), False)
            else:
                print("WARNING: 'CRM getuser API uri not set, test full validity can't be determined")
            no_sync_user.delete()
