# coding:utf-8
import re

from django.conf import settings
from django.test import TestCase, Client

from photologue_ladiaria.management.commands.utopiacms_photosizes import Command


class ArticleTestCase(TestCase):

    fixtures = ['test']
    http_host_header_param = {'HTTP_HOST': settings.SITE_DOMAIN}
    # add articles urls here, but keep the other
    urls_to_test = [
        {'url': '/spinoff/articulo/2020/11/test-article4/', 'headers': http_host_header_param},
        {'url': '/spinoff/articulo/2020/11/test-article4/', 'amp': True, 'headers': http_host_header_param},
        {'url': '/test/articulo/2020/11/test-humor1/', 'headers': http_host_header_param},
        {'url': '/test/articulo/2020/11/test-humor1/', 'amp': True, 'headers': http_host_header_param},
        {'url': '/articulo/2020/11/test-article/', 'headers': http_host_header_param},
        {'url': '/articulo/2020/11/test-article/', 'amp': True, 'headers': http_host_header_param},
        {'url': '/spinoff/articulo/2020/11/test-article2/', 'headers': http_host_header_param},
        {'url': '/spinoff/articulo/2020/11/test-article2/', 'amp': True, 'headers': http_host_header_param},
    ]

    def setUp(self):
        # run command for photo sizes
        self.setup_photo_sizes()

    def setup_photo_sizes(self):
        command = Command()
        command.handle()

    def test01_article_response(self):
        c = Client()
        with self.settings(DEBUG=True):
            for item in self.urls_to_test[:2]:
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                # test success response
                self.assertEqual(response.status_code, 200, (response.status_code, response))
                # test article photo relationship
                self.assertIsNotNone(response.context['article'].photo)
                # test photo path in the context
                self.assertEqual(response.context['article'].photo.image, 'fixtures/test_pou_img.jpg')

                content = response.content.decode()
                context_article = response.context['article']

                # test the image caption render
                self.assertRegex(content, '<p.*>{}</p>'.format(str(context_article.photo.caption)))
                # test image src values for render, at least 3 sizes count in template
                self.assertGreater(content.count('/media/fixtures/cache/test_pou_img_'), 3)
                # test meta noindex for not humor articles
                self.assertNotIn('<meta name="robots" content="noindex">', content)

            # status 200 also for the display param with a "not considered" value
            item = self.urls_to_test[0]
            response = c.get(item['url'], {'display': 'x'}, **item.get('headers', {}))
            self.assertEqual(response.status_code, 200, (response.status_code, response))

    def test02_humor_article_noindex(self):
        c = Client()
        with self.settings(DEBUG=True, CORE_SATIRICAL_SECTIONS=('humor', )):
            for item in self.urls_to_test[2:4]:
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                content = response.content.decode()
                # test meta noindex for humor articles
                self.assertIn('<meta name="robots" content="noindex">', content)

    def test03_alt_content_fields_unset(self):
        # Tests the render result html for an article (without the "alt" fields set) and also the same in AMP
        c = Client()
        with self.settings(DEBUG=True):
            for item in self.urls_to_test[4:6]:
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                content = response.content.decode()
                # using re instead of assertRegex to match accross all content "lines"
                self.assertIsNotNone(
                    re.match(r".*<head>.*<title>test article \| .*</title>.*", content, re.DOTALL), content
                )
                self.assertIn('<meta name="description" content="test.">', content)
                self.assertIn('<meta property="og:title" content="test article">', content)
                self.assertIn('<meta property="og:description" content="test.">', content)
                self.assertIn('"headline": "test article"', content)
                self.assertIn('"description": "test."', content)

    def test04_alt_content_fields_set(self):
        # Tests the render result html for an article (without the "alt" fields set) and also the same in AMP
        c = Client()
        with self.settings(DEBUG=True):
            for item in self.urls_to_test[6:]:
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))
                content = response.content.decode()
                # using re instead of assertRegex to match accross all content "lines"
                self.assertIsNotNone(
                    re.match(r".*<head>.*<title>test article2 \| .*</title>.*", content, re.DOTALL), content
                )
                self.assertIn('<meta name="description" content="test2.">', content)
                self.assertIn('<meta property="og:title" content="article2 alternative title">', content)
                self.assertIn('<meta property="og:description" content="article2 alternative desc">', content)
                self.assertIn('"headline": "article2 alternative title"', content)
                self.assertIn('"description": "article2 alternative desc"', content)
