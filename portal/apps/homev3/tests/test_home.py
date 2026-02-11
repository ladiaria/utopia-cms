# coding:utf-8

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
    amp_detection = '<link rel="amphtml"'

    def test1_home(self):
        # a way to make this test fail by settings (may be useful to know if you get noticed when tests are failing)
        self.assertFalse(getattr(settings, "HOMEV3_FIRST_TEST_SHOULD_FAIL", False))

        c = Client()
        with self.settings(DEBUG=True, DEFAULT_PUB="default"):
            for item in self.urls_to_test:
                response = c.get(item['url'], **item.get('headers', {}))
                if item.get('amp') and self.amp_detection in response.content.decode():
                    response = c.get(item['url'], {'display': 'amp'}, **item.get('headers', {}))
                    self.assertEqual(response.status_code, 200)
            # status 200 also for the display param with a "not considered" value
            item = self.urls_to_test[0]
            response = c.get(item['url'], {'display': 'x'}, **item.get('headers', {}))
            self.assertEqual(response.status_code, 200)
            # and if AMP is enabled, with display=amp should return Forbidden
            response = c.get(item['url'], {'display': 'amp'}, **item.get('headers', {}))
            self.assertEqual(response.status_code, 403 if settings.CORE_ARTICLE_DETAIL_ENABLE_AMP else 200)

    def test2_home_logged_in(self):
        password, user = User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        c = Client()
        c.login(username=user.username, password=password)
        with self.settings(DEBUG=True, DEFAULT_PUB="default"):
            for item in self.urls_to_test:
                response = c.get(item['url'], **item.get('headers', {}))
                self.assertEqual(response.status_code, 200)
                if item.get('amp') and self.amp_detection in response.content.decode():
                    response = c.get(item['url'], {'display': 'amp'}, **item.get('headers', {}))
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
                response = c.get(item['url'], **item.get('headers', {}))
                self.assertEqual(response.status_code, 200)
                if item.get('amp') and self.amp_detection in response.content.decode():
                    response = c.get(item['url'], {'display': 'amp'}, **item.get('headers', {}))
                    self.assertEqual(response.status_code, 200)

        # article_with_iframe_in_extension
        response = c.get('/articulo/2024/07/test-article9/', **self.http_host_header_param)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.amp_detection, response.content.decode())
        # article_with_valid_script_in_extension
        response = c.get("/articulo/2020/11/test-full-restricted1/", **self.http_host_header_param)
        self.assertEqual(response.status_code, 200)
        if settings.CORE_ARTICLE_DETAIL_ENABLE_AMP:
            self.assertIn(self.amp_detection, response.content.decode())
        else:
            self.assertNotIn(self.amp_detection, response.content.decode())
        # article_with_invalid_script_in_extension
        response = c.get("/spinoff/articulo/2020/11/test-article7/", **self.http_host_header_param)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.amp_detection, response.content.decode())
