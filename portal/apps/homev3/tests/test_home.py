# coding:utf-8
from __future__ import unicode_literals

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from core.factories import UserFactory


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

    def test1_home(self):
        # a way to make this test fail by settings (may be useful to know if you get noticed when tests are failing)
        self.assertFalse(getattr(settings, "HOMEV3_FIRST_TEST_SHOULD_FAIL", False))

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

    def test2_home_logged_in(self):
        password, user = User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        c = Client()
        c.login(username=user.username, password=password)
        with self.settings(DEBUG=True, DEFAULT_PUB="default"):
            for item in self.urls_to_test:
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                self.assertEqual(response.status_code, 200)

    def test3_home_staff_logged_in(self):
        password, user = User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.is_staff = True
        user.save()
        c = Client()
        c.login(username=user.username, password=password)
        with self.settings(DEBUG=True, DEFAULT_PUB="default"):
            for item in self.urls_to_test + ({'url': '/admin/'}, ):
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                self.assertEqual(response.status_code, 200)
