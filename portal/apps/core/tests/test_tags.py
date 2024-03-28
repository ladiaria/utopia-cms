# coding:utf-8
from django.test import TestCase, Client
from django.template.defaultfilters import slugify


class TagTestCase(TestCase):

    def test_url_redirect(self):
        # TODO: load fixture and assert 200 ok (now is returning 404)
        c = Client()
        tag_slug = 'tecnología'  # to be redirected to the non-accent version (í->i)
        response = c.get('/tags/{}/'.format(tag_slug), follow=True)
        # check if it's got the redirects in the chain
        self.assertGreater(len(response.redirect_chain), 0)
        # check if the new slugified tag_name is present in the new url
        self.assertIn(slugify(tag_slug), response.request['PATH_INFO'])
