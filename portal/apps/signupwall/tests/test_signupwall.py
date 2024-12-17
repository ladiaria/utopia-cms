# coding:utf-8
from html2text import html2text

from django.conf import settings
from django.test import TestCase, tag
from django.test.client import Client
from django.contrib.auth.models import User
from django.utils.lorem_ipsum import paragraph

from libs.scripts.pwclear import pwclear
from core.models import Publication, Article
from core.factories import UserFactory

from . import label_content_not_available, label_to_continue_reading, label_exclusive, label_exclusive4u


class SignupwallTestCase(TestCase):
    fixtures = ['test']
    http_host_header_param = {'HTTP_HOST': settings.SITE_DOMAIN}

    def no_redirection_for_restricted_article(self, c, restricted_msg, can_read=False, is_subscriber_any=False):
        with self.settings(CORE_RESTRICTED_PUBLICATIONS=("restrictedpub",)):
            a = Article.objects.get(slug="test-restricted1")
            lorem_paragraph = paragraph()
            a.body += f"\n\n{lorem_paragraph}"
            a.save()
            response = c.get(a.get_absolute_url(), **self.http_host_header_param)
            response_content = response.content.decode()
            self.assertEqual(response.status_code, 200)
            self.assertIn(lorem_paragraph if can_read else restricted_msg, response_content)
            assertion = self.assertNotIn if can_read else self.assertIn
            if can_read or is_subscriber_any:
                assertion(label_content_not_available, response_content)

    def no_redirection_for_full_restricted_article(self, c, restricted_msg, can_read=False, is_subscriber_any=False):
        a = Article.objects.get(slug="test-full-restricted1")
        lorem_paragraph = paragraph()
        a.body += f"\n\n{lorem_paragraph}"
        a.save()
        response = c.get(a.get_absolute_url(), **self.http_host_header_param)
        response_content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            lorem_paragraph if is_subscriber_any else restricted_msg,
            response_content,
            html2text(response_content).rstrip(),
        )
        assertion = self.assertNotIn if can_read else self.assertIn
        if can_read or is_subscriber_any:
            assertion(
                (
                    label_exclusive if can_read else label_exclusive4u
                ) if is_subscriber_any else label_content_not_available,
                response_content,
                html2text(response_content).rstrip(),
            )

    def user_faces_wall(self, c, restricted_msg=label_exclusive, is_subscriber_any=False):
        for i in range(settings.SIGNUPWALL_MAX_CREDITS - 1):
            a = Article.objects.create(type="NE", headline='test%d' % (i + 1))
            response = c.get(a.get_absolute_url(), **self.http_host_header_param)
            self.assertEqual(response.status_code, 200)
            response_content = response.content.decode()
            self.assertIn("Tu cuenta", response_content)
            self.assertIn("Te queda", response_content)
            self.assertNotIn(label_to_continue_reading, response_content)

        a = Article.objects.create(type="NE", headline='test_last')
        r = c.get(a.get_absolute_url(), **self.http_host_header_param)
        self.assertEqual(r.status_code, 200)
        response_content = r.content.decode()
        self.assertIn("Tu cuenta", response_content)
        self.assertIn("Este es tu último", response_content)

        a = Article.objects.create(headline='test_walled')
        r = c.get(a.get_absolute_url(), **self.http_host_header_param)
        if settings.SIGNUPWALL_RISE_REDIRECT:
            self.assertEqual(r.status_code, 302)
            r = c.get(r.headers["location"],  **self.http_host_header_param)
            response_content = r.content.decode()
            self.assertIn("Suscribite para continuar leyendo este artículo", response_content)

        # no redirection for restricted / full restricted articles
        self.no_redirection_for_restricted_article(c, restricted_msg, is_subscriber_any=is_subscriber_any)
        self.no_redirection_for_full_restricted_article(c, restricted_msg, is_subscriber_any=is_subscriber_any)

    def test01_anon_faces_wall(self):
        pwclear()
        c = Client()
        for i in range(settings.SIGNUPWALL_ANON_MAX_CREDITS):
            a = Article.objects.create(headline='test%d' % (i + 1))
            response = c.get(a.get_absolute_url(), **self.http_host_header_param)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(label_to_continue_reading, response.content.decode())

        a = Article.objects.create(headline='test_walled')
        response = c.get(a.get_absolute_url(), **self.http_host_header_param)
        if settings.SIGNUPWALL_RISE_REDIRECT:
            self.assertEqual(response.status_code, 302)
            response = c.get(response.headers["location"],  **self.http_host_header_param)
            self.assertIn("Registrate para acceder a", response.content.decode())

        # no redirection for restricted / full restricted articles.
        self.no_redirection_for_restricted_article(c, label_exclusive)
        self.no_redirection_for_full_restricted_article(c, label_exclusive)

    def test02_non_subscriber_faces_wall(self):
        pwclear()
        c, password, user = Client(), User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        c.login(username=user.username, password=password)
        self.user_faces_wall(c)

    @tag('skippable')
    def test03_subscriber_to_non_default_pub_faces_wall(self):
        # TODO: this test fails because the user is not a subscriber to the spinoff pub:
        #       Inconsistent html is rendered to the user with de badge of "content unlocked for your subscription" and
        #       and empty article body (no content).
        #       This is happenning in utopia-only and "ladiaria" custom environments but not in "cambio".
        pwclear()
        c, password, user = Client(), User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        # save spinoff pub to generate permission obj
        Publication.objects.get(slug="spinoff").save()
        user.subscriber.is_subscriber("spinoff", operation="set")
        c.login(username=user.username, password=password)
        self.user_faces_wall(c, label_content_not_available, True)

    @tag('skippable')
    def test04_subscriber_passes_wall(self):
        # TODO: it seems that this got broken in a similar way as test03
        pwclear()
        c, password, user = Client(), User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        # update 'default' pub to ensure slug in settings and update/generate Permission object
        try:
            p = Publication.objects.get(slug="default")
            p.slug = settings.DEFAULT_PUB
            p.save()
        except Publication.DoesNotExist:
            pass
        user.subscriber.is_subscriber(operation="set")
        c.login(username=user.username, password=password)

        for i in range(settings.SIGNUPWALL_MAX_CREDITS + 1):
            a = Article.objects.create(headline='test%d' % (i + 1))
            response = c.get(a.get_absolute_url(), **self.http_host_header_param)
            self.assertEqual(response.status_code, 200)
            response_content = response.content.decode()
            self.assertIn("Tu cuenta", response_content)
            self.assertNotIn("Te queda", response_content)

        # no redirection for restricted /full restricted articles and can read it
        self.no_redirection_for_restricted_article(c, label_exclusive, True)
        self.no_redirection_for_full_restricted_article(c, label_exclusive, True)
