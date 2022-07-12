# coding:utf8
from django.test import TestCase, Client
from django.template.defaultfilters import slugify


class TagTestCase(TestCase):

    def test_url_redirect(self):
        c = Client()
        tag_slug = 'tegnología'
        response = c.get('/tags/{}/'.format(tag_slug), follow=True)
        # check if it's got the redirects in the chain
        self.assertGreater(len(response.redirect_chain), 0)
        # check if the new slugified tag_name is present in the new url
        self.assertIn(slugify(tag_slug), response.request['PATH_INFO'])
