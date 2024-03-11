# coding:utf-8
from __future__ import unicode_literals

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from apps import mongo_db
from libs.scripts.pwclear import phone_subscription_log_clear
from core.factories import UserFactory


class SubscribeTestCase(TestCase):

    fixtures = ['test']
    var = {"test01_planslug": "DDIGM"}

    def check_one_entry(self, response):
        self.assertEqual(response.status_code, 200)
        if mongo_db is not None:
            self.assertEqual(mongo_db.phone_subscription_log.count_documents({}), 1)
        elif settings.DEBUG:
            print("WARNING: mongo_db is None, %s should be tested again with a 'working mongoDB' config." % type(self))

    def subscribe_requests(self, c, blocked_phone_prefix):
        response = c.get('/usuarios/planes/', follow=True)
        self.assertEqual(response.status_code, 200)
        response_content = response.content.decode()
        self.assertIn("Suscripción digital", response_content)
        planslug = self.var["test01_planslug"]
        phone_subscription_log_clear()
        user = response.wsgi_request.user
        my_email = user.email if user.is_authenticated else "userone@gmail.com"
        post_data = {
            "first_name": "User One",
            "email": my_email,
            "phone": "17051400",
            "password": User.objects.make_random_password(),
            "preferred_time": 1,
            "terms_and_conds_accepted": True,
            "subscription_type_prices": planslug,
            "payment_type": "tel",
        }
        post_data.update(self.var.get("test01_extra_post_data", {}))
        response = c.post('/usuarios/suscribite/%s/' % planslug, post_data, follow=True)
        self.check_one_entry(response)
        response_content = response.content.decode()
        self.assertIn("Recibimos tu información", response_content)
        display_msg = "Mientras tanto"
        if response.wsgi_request.user.is_authenticated:
            self.assertNotIn(display_msg, response_content)
        else:
            self.assertIn(display_msg, response_content)
        # try now to submit again but directly in the phone subscription url, we should see a "Already" smth.
        post_data_direct = {
            "first_name": post_data["first_name"], "phone": post_data["phone"], "time": post_data["preferred_time"]
        }
        response = c.post('/usuarios/suscribite-por-telefono/', post_data_direct)
        self.check_one_entry(response)
        response_content = response.content.decode()
        self.assertIn("Ya recibimos tu información", response_content)
        self.assertNotIn(display_msg, response_content)
        # try again with a blocklisted phone
        post_data_direct["phone"] = blocked_phone_prefix + "0001"
        response = c.post('/usuarios/suscribite-por-telefono/', post_data_direct)
        self.check_one_entry(response)
        response_content = response.content.decode()
        self.assertIn("Información no válida", response_content)
        self.assertNotIn(display_msg, response_content)
        # try again with a valid phone and clearing mongo log
        phone_subscription_log_clear()
        post_data_direct["phone"] = "1110001"
        response = c.post('/usuarios/suscribite-por-telefono/', post_data_direct)
        self.check_one_entry(response)
        response_content = response.content.decode()
        self.assertIn("Recibimos tu información", response_content)
        self.assertNotIn(display_msg, response_content)
        # try again the same without clearing log => "already" message
        response = c.post('/usuarios/suscribite-por-telefono/', post_data_direct)
        self.check_one_entry(response)
        response_content = response.content.decode()
        self.assertIn("Ya recibimos tu información", response_content)
        self.assertNotIn(display_msg, response_content)

    def test01_subscribe_landing(self):
        c, blocked_phone_prefix = Client(), "666555"
        with self.settings(DEBUG=True, TELEPHONES_BLOCKLIST=[blocked_phone_prefix]):
            # anon requests
            self.subscribe_requests(c, blocked_phone_prefix)
            # logged in requests
            password, user = User.objects.make_random_password(), UserFactory()
            user.set_password(password)
            user.save()
            c.login(username=user.username, password=password)
            self.subscribe_requests(c, blocked_phone_prefix)

    def test02_subscribe_landing_logged_in(self):
        password, user = User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        c = Client()
        c.login(username=user.username, password=password)
        with self.settings(DEBUG=True):
            response = c.get('/usuarios/planes/', follow=True)
            self.assertEqual(response.status_code, 200)
            response_content = response.content.decode()
            self.assertNotIn("Creá tu cuenta", response_content)
            self.assertIn("Suscripción digital", response_content)

    def test03_user_profile(self):
        password, user = User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        c = Client()
        c.login(username=user.username, password=password)
        with self.settings(DEBUG=True):
            response = c.get('/usuarios/perfil/editar/')
            self.assertEqual(response.status_code, 200)
            response_content = response.content.decode()
            self.assertIn("Tu cuenta", response_content)
