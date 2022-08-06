# coding:utf8
from __future__ import unicode_literals
import requests

from django.core.urlresolvers import reverse
from django.test import LiveServerTestCase
from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission

from core.models import Article


class SignupwallTestCase(LiveServerTestCase):

    def login(self, name_or_mail, password):
        data = {'name_or_mail': name_or_mail, 'password': password}
        s = requests.Session()
        s.get(self.live_server_url + reverse("account-login"))
        csrftoken = s.cookies.get('csrftoken')
        if csrftoken:
            data['csrfmiddlewaretoken'] = csrftoken
        r = s.post(self.live_server_url + reverse("account-login"), data=data)
        r.raise_for_status()
        return s

    def get(self, url, user, session):
        request = self.factory.get(url)
        request.user = user
        request.session = session
        return request

    def test_anon_faces_wall(self):
        a1 = Article(headline='test1')
        a1.save()
        s = requests.Session()
        response = s.get(self.live_server_url + a1.get_absolute_url())
        self.assertNotIn("Nos gustaría que te suscribieras", response.text)
        a2 = Article(headline='test2')
        a2.save()
        response = s.get(self.live_server_url + a2.get_absolute_url())
        self.assertNotIn("Nos gustaría que te suscribieras", response.text)
        a3 = Article(headline='test3')
        a3.save()
        response = s.get(self.live_server_url + a3.get_absolute_url())
        self.assertIn("Nos gustaría que te suscribieras", response.text)

    def test_non_subscriber_faces_wall(self):
        user = User.objects.create_user('user1', 'u1@ladiaria.com.uy', 'ldu1')
        s = self.login(user.username, 'ldu1')
        a1 = Article(headline='test1')
        a1.save()
        response = s.get(self.live_server_url + a1.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn(user.username, response.text)
        self.assertNotIn("Nos gustaría que te suscribieras", response.text)

        a2 = Article(headline='test2')
        a2.save()
        response = s.get(self.live_server_url + a2.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn(user.username, response.text)
        self.assertNotIn("Nos gustaría que te suscribieras", response.text)

        a3 = Article(headline='test3')
        a3.save()
        r = s.get(self.live_server_url + a3.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertIn(user.username, r.text)
        self.assertIn("Nos gustaría que te suscribieras", r.text)

    def test_subscriber_passes_wall(self):
        user = User.objects.create_user('user2', 'u2@ladiaria.com.uy', 'ldu2')
        user.user_permissions.add(Permission.objects.get(codename='es_suscriptor_default'))
        s = self.login(user.username, 'ldu2')
        a1 = Article(headline='test1')
        a1.save()
        response = s.get(self.live_server_url + a1.get_absolute_url())
        self.assertIn(user.username, response.text)
        self.assertNotIn("Nos gustaría que te suscribieras", response.text)

        a2 = Article(headline='test2')
        a2.save()
        response = s.get(self.live_server_url + a2.get_absolute_url())
        self.assertIn(user.username, response.text)
        self.assertNotIn("Nos gustaría que te suscribieras", response)

        a3 = Article(headline='test3')
        a3.save()
        response = s.get(self.live_server_url + a3.get_absolute_url())
        self.assertIn(user.username, response.text)
        self.assertNotIn("Nos gustaría que te suscribieras", response.text)


SignupwallTestCase = override_settings(DEBUG=True)(SignupwallTestCase)
