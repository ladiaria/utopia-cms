# coding:utf8
from __future__ import unicode_literals
import unittest

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User


class SubscribeTestCase(TestCase):

    fixtures = ['test']

    def test_subscribe(self):
        c = Client()
        with self.settings(DEBUG=True):
            response = c.get('/usuarios/planes/', follow=True)
            self.assertEqual(response.status_code, 200)

    @unittest.skip("social_auth tables needed")
    def test_subscribe_logged_in(self):
        # TODO 2nd release: this test fails because social_auth tables are not present.
        #                   maybe this will be fixed using Django1.11 with a newer version of social_django
        email, password = 'u1@example.com', User.objects.make_random_password()
        user = User.objects.create_user(email, email, password)
        user.is_active = True
        user.save()
        c = Client()
        c.login(username=email, password=password)
        with self.settings(DEBUG=True):
            response = c.get('/usuarios/planes/', follow=True)
            self.assertEqual(response.status_code, 200)

    @unittest.skip("social_auth tables needed")
    def test_user_profile(self):
        # TODO: same as test_subscribe_logged_in
        email, password = 'u1@example.com', User.objects.make_random_password()
        user = User.objects.create_user(email, email, password)
        user.is_active = True
        user.save()
        c = Client()
        c.login(username=email, password=password)
        with self.settings(DEBUG=True):
            response = c.get('/usuarios/perfil/editar/')
            self.assertEqual(response.status_code, 200)
