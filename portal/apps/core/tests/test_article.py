# coding:utf-8
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
        {'url': '/test/articulo/2020/11/test-humor1/', 'amp': True, 'headers': http_host_header_param}
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
            for item in self.urls_to_test[:2]:  # TODO: fix for all urls
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
                self.assertRegex(content, r'<p.*>{}</p>'.format(str(context_article.photo.caption)))
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
            for item in self.urls_to_test[2:]:  # TODO: fix for all urls
                response = c.get(item['url'], {'display': 'amp'} if item.get('amp') else {}, **item.get('headers', {}))

                content = response.content.decode()
                # test meta noindex for humor articles
                self.assertIn('<meta name="robots" content="noindex">', content)
