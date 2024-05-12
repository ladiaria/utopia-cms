import time
from selenium.webdriver.common.by import By

from django.conf import settings
from django.test import tag
from django.contrib.auth.models import User

from libs.scripts.pwclear import pwclear
from core.models import Publication, Article
from core.factories import UserFactory

from . import LiveServerSeleniumTestCase, label_content_not_available, label_to_continue_reading, label_exclusive


@tag('selenium')
class SignupwallAMPTestCase(LiveServerSeleniumTestCase):
    # TODO: try to undouble the "//" in the URLs

    fixtures = ['test']

    def get_title_displayed(self):
        result = []
        for css_sel in (".signupwall-header p", ".ld-snackbar__title"):
            result.extend([e.text for e in self.selenium.find_elements(By.CSS_SELECTOR, css_sel) if e.is_displayed()])
        return "".join(result)

    def login(self, user, password):
        self.selenium.get(f"{self.server_url}{settings.LOGOUT_URL}")
        self.selenium.get(f"{self.server_url}{settings.LOGIN_URL}")

        username_input = self.selenium.find_element(By.NAME, "name_or_mail")
        username_input.send_keys(user.username)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(password)

        self.jsclick('#main-content>div.container>main>div>div>form>div.row>div>button')

    def restricted_article(self, restricted_title):
        with self.settings(CORE_RESTRICTED_PUBLICATIONS=("restrictedpub",)):
            a = Article.objects.get(slug="test-restricted1")
            self.selenium.get(f"{self.server_url}{a.get_absolute_url()}?display=amp")
            time.sleep(2)
            self.assertEqual(restricted_title, self.get_title_displayed())

    def user_faces_wall(self, restricted_title=label_exclusive):
        for i in range(settings.SIGNUPWALL_MAX_CREDITS - 1):
            a = Article.objects.create(headline='test%d' % (i + 1))
            self.selenium.get(f"{self.server_url}{a.get_absolute_url()}?display=amp")
            time.sleep(2)
            title_displayed = self.get_title_displayed()
            self.assertIn("Te queda", title_displayed)
            self.assertNotEqual(label_to_continue_reading, title_displayed)

        a = Article.objects.create(headline='test_last')
        self.selenium.get(f"{self.server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertIn("Este es tu último", self.get_title_displayed())

        a = Article.objects.create(headline='test_walled')
        self.selenium.get(f"{self.server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertIn("Llegaste al límite", self.get_title_displayed())

        # restricted articles
        self.restricted_article(restricted_title)

    def test01_anon_faces_wall(self):
        self.set_current_site_domain()
        pwclear()
        """
        TODO: A module that also works here, interesting thing to investigate (pip install browserist)
        from browserist import Browser
        with Browser() as browser:
            browser.open.url(...)
        """
        self.selenium.get(f"{self.server_url}{settings.LOGOUT_URL}")

        for i in range(settings.SIGNUPWALL_ANON_MAX_CREDITS):
            a = Article.objects.create(headline='test%d' % (i + 1))
            self.selenium.get(f"{self.server_url}{a.get_absolute_url()}?display=amp")
            time.sleep(2)
            self.assertNotEqual(label_to_continue_reading, self.get_title_displayed())

        a = Article.objects.create(headline='test_walled')
        self.selenium.get(f"{self.server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertEqual(label_to_continue_reading, self.get_title_displayed())

        # restricted articles
        self.restricted_article(label_exclusive)

    def test02_non_subscriber_faces_wall(self):
        self.set_current_site_domain()
        pwclear()
        password, user = User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        self.login(user, password)
        self.user_faces_wall()

    def test03_non_default_pub_subscriber_faces_wall(self):
        self.set_current_site_domain()
        pwclear()
        password, user = User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        # save spinoff pub to generate permission obj
        Publication.objects.get(slug="spinoff").save()
        user.subscriber.is_subscriber("spinoff", operation="set")
        self.login(user, password)
        self.user_faces_wall(label_content_not_available)

    def test04_subscriber_passes_wall(self):
        self.set_current_site_domain()
        pwclear()
        password, user = User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        # save or update 'default' pub to ensure slug in settings and update/generate Permission object
        try:
            Publication.objects.get(slug=settings.DEFAULT_PUB).save()
        except Publication.DoesNotExist:
            try:
                p = Publication.objects.get(slug="default")
                p.slug = settings.DEFAULT_PUB
                p.save()
            except Publication.DoesNotExist:
                pass
        user.subscriber.is_subscriber(operation="set")
        self.login(user, password)

        for i in range(settings.SIGNUPWALL_MAX_CREDITS + 1):
            a = Article.objects.create(headline='test%d' % (i + 1))
            self.selenium.get(f"{self.server_url}{a.get_absolute_url()}?display=amp")
            time.sleep(2)
            title_displayed = self.get_title_displayed()
            self.assertNotIn("Te queda", title_displayed)
            self.assertNotIn(label_to_continue_reading, title_displayed)

        # restricted articles allowed
        self.restricted_article("")
