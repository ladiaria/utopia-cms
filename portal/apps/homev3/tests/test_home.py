# coding:utf-8
from __future__ import unicode_literals

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User


class HomeTestCase(TestCase):

    fixtures = ['test']
    http_host_header_param = {'HTTP_HOST': settings.SITE_DOMAIN}
    urls_to_test = (
        {'url': '/'},
        {'url': '/periodista/test-journalist/'},
        {'url': '/columnista/test-columnist/'},
        {'url': '/test/'},
        {'url': '/tags/test/'},
        {'url': '/seccion/news/'},
        {'url': '/seccion/areasection/'},
        {'url': '/articulo/2020/11/test-article/', 'headers': http_host_header_param},
        {'url': '/articulo/2020/11/test-article/', 'amp': True, 'headers': http_host_header_param},
        {'url': '/spinoff/'},
        {'url': '/spinoff/articulo/2020/11/test-article2/', 'headers': http_host_header_param},
        {'url': '/spinoff/articulo/2020/11/test-article2/', 'amp': True, 'headers': http_host_header_param},
        {'url': '/test/articulo/2020/11/test-article3/', 'headers': http_host_header_param},
        {'url': '/test/articulo/2020/11/test-article3/', 'amp': True, 'headers': http_host_header_param},
    )

    def test_home(self):
        c = Client()
        with self.settings(DEBUG=True, DEFAULT_PUB="default"):
            for item in self.urls_to_test:
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                self.assertEqual(response.status_code, 200, (response.status_code, response))
            # status 200 also for the display param with a "not considered" value
            item = self.urls_to_test[0]
            response = c.get(item['url'], {'display': 'x'}, **item.get('headers', {}))
            self.assertEqual(response.status_code, 200, (response.status_code, response))
            # and with display=amp should return Forbidden
            response = c.get(item['url'], {'display': 'amp'}, **item.get('headers', {}))
            self.assertEqual(response.status_code, 403, (response.status_code, response))

    def test_home_logged_in(self):
        email, password = 'u1@gmail.com', User.objects.make_random_password()
        user = User.objects.create_user(email, email, password)
        user.is_active = True
        user.save()
        c = Client()
        c.login(username=email, password=password)
        with self.settings(DEBUG=True, DEFAULT_PUB="default"):
            for item in self.urls_to_test:
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                self.assertEqual(response.status_code, 200)

    def test_home_staff_logged_in(self):
        email, password = 'u1@gmail.com', User.objects.make_random_password()
        user = User.objects.create_user(email, email, password)
        user.is_active, user.is_staff = True, True
        user.save()
        c = Client()
        c.login(username=email, password=password)
        with self.settings(DEBUG=True, DEFAULT_PUB="default"):
            for item in self.urls_to_test + ({'url': '/admin/'}, ):
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                self.assertEqual(response.status_code, 200)
