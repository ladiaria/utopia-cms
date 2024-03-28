# coding:utf-8
from __future__ import print_function
from __future__ import unicode_literals

from builtins import range
import string
import random

from django.test import TestCase
from django.contrib.auth.models import User


class CRMSyncTestCase(TestCase):

    def test_sync(self):
        email, password = 'u1@ld.com.uy', User.objects.make_random_password()
        user = User.objects.create_user(email, email, password)
        user.is_active = True
        user.save()
        self.assertIsNotNone(user.subscriber)
        user.subscriber.contact_id = 1
        user.subscriber.save()
        email = '%s@ladiaria.com.uy' % ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        user.email = email
        user.save()
        # TODO: make next check here, programatically
        print("Check if the customer with id=1 in CRM has the email <%s>" % email)
