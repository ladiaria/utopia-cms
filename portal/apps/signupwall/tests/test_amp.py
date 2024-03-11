import time
from selenium.webdriver.common.by import By

from django.conf import settings
from django.test import tag
from django.contrib.auth.models import User

from libs.scripts.pwclear import pwclear
from core.models import Publication, Article
from core.factories import UserFactory

from . import LiveServerSeleniumTestCase


@tag('selenium')
class SignupwallAMPTestCase(LiveServerSeleniumTestCase):
    # TODO: try to undouble the "//" in the URLs

    fixtures = ['test']

    def get_title_displayed(self):
        return "".join(
            [e.text for e in self.selenium.find_elements(By.CSS_SELECTOR, ".ld-snackbar__title") if e.is_displayed()]
        )

    def login(self, user, password):
        server_url = settings.SITE_URL
        self.selenium.get(f"{server_url}usuarios/salir/")
        self.selenium.get(f"{server_url}usuarios/entrar/")

        username_input = self.selenium.find_element(By.NAME, "name_or_mail")
        username_input.send_keys(user.username)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(password)

        self.jsclick('#main-content>div.container>main>div>div>form>div.row>div>button')

    def user_faces_wall(self, restricted_title="Exclusivo para suscripción digital de pago"):
        server_url = settings.SITE_URL
        for i in range(settings.SIGNUPWALL_MAX_CREDITS - 1):
            a = Article.objects.create(headline='test%d' % (i + 1))
            self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
            time.sleep(2)
            title_displayed = self.get_title_displayed()
            self.assertIn("Te queda", title_displayed)
            self.assertNotEqual("Para seguir leyendo ingresá o suscribite", title_displayed)

        a = Article.objects.create(headline='test_last')
        self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertIn("Este es tu último", self.get_title_displayed())

        a = Article.objects.create(headline='test_walled')
        self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertIn("Llegaste al límite", self.get_title_displayed())

        # restricted articles
        a = Article.objects.get(slug="test-restricted1")
        self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertEqual(restricted_title, self.get_title_displayed())

    def test01_anon_faces_wall(self):
        self.set_current_site_domain()
        pwclear()
        server_url = settings.SITE_URL
        self.selenium.get(f"{server_url}usuarios/salir/")

        for i in range(settings.SIGNUPWALL_ANON_MAX_CREDITS):
            a = Article.objects.create(headline='test%d' % (i + 1))
            self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
            time.sleep(2)
            self.assertNotEqual("Para seguir leyendo ingresá o suscribite", self.get_title_displayed())

        a = Article.objects.create(headline='test_walled')
        self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertEqual("Para seguir leyendo ingresá o suscribite", self.get_title_displayed())

        # restricted articles
        a = Article.objects.get(slug="test-restricted1")
        self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertEqual("Exclusivo para suscripción digital de pago", self.get_title_displayed())

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
        self.user_faces_wall("Contenido no disponible con tu suscripción actual")

    def test04_subscriber_passes_wall(self):
        self.set_current_site_domain()
        pwclear()
        server_url, password, user = settings.SITE_URL, User.objects.make_random_password(), UserFactory()
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
            self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
            time.sleep(2)
            title_displayed = self.get_title_displayed()
            self.assertNotIn("Te queda", title_displayed)
            self.assertNotIn("Para seguir leyendo ingresá o suscribite", title_displayed)

        # restricted articles allowed
        a = Article.objects.get(slug="test-restricted1")
        self.selenium.get(f"{server_url}{a.get_absolute_url()}?display=amp")
        time.sleep(2)
        self.assertEqual("", self.get_title_displayed())
