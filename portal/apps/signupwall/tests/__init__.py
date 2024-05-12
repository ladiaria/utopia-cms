from os.path import join

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# keep commented according lines to use chrome or firefox:
from selenium.webdriver.chrome.options import Options as ChromeOptions
# from selenium.webdriver.firefox.options import Options as FirefoxOptions
# from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from django.conf import settings
from django.core.servers.basehttp import ThreadedWSGIServer
from django.contrib.sites.models import Site
from django.contrib.staticfiles.testing import LiveServerTestCase
from django.test.testcases import LiveServerThread, QuietWSGIRequestHandler


label_content_not_available = "Contenido no disponible con tu suscripción actual"
label_to_continue_reading = "Para seguir leyendo ingresá o suscribite"
label_exclusive = "Exclusivo para suscripción digital de pago"


class LiveServerThreadWithReuse(LiveServerThread):
    """
    This miniclass overrides _create_server to allow port reuse. This avoids creating
    "address already in use" errors for tests that have been run subsequently.
    taken from: https://stackoverflow.com/a/51756256
    """

    def _create_server(self, connections_override=True):
        return ThreadedWSGIServer((self.host, self.port), QuietWSGIRequestHandler, allow_reuse_address=True)


class LiveServerSeleniumTestCase(LiveServerTestCase):
    host = settings.SITE_DOMAIN
    port = settings.TESTING_PORT
    url_scheme = settings.URL_SCHEME
    server_url = "%s://%s" % (url_scheme, host)
    server_thread_class = LiveServerThreadWithReuse
    waitsecs = getattr(settings, "SIGNUPWALL_SELENIUM_DEFAULT_WAITSECS", 30)

    @classmethod
    def setUpClass(cls):
        # chrome setup:
        headless = settings.TESTING_CHROME_HEADLESS
        chrome_options = ChromeOptions()
        if headless:
            chrome_options.add_argument('--headless')

        """
        Uncomment next line to test in chrome-android using an android device listed in "adb".
        NOTE and TODO: Chrome in Android is very difficult because there seems to be no way to eliminate the SSL
        warning, and Firefox on Android is not supported "native" like this option for Chrome; but, we can better try
        here to launch a mobile emulation in the desktop browsers, ex: https://stackoverflow.com/a/63798638/2292933
        """
        # chrome_options.add_experimental_option('androidPackage', 'com.android.chrome')
        driver, implicitly_wait = webdriver.Chrome(options=chrome_options), 0.5
        driver.implicitly_wait(implicitly_wait)
        driver.delete_all_cookies()
        cls.selenium = driver

        # firefox setup (TODO: check):
        """
        ff_options = FirefoxOptions()
        ff_options.headless = headless
        profile = webdriver.FirefoxProfile(settings.TESTING_FF_PROFILE)
        profile.set_preference("dom.webdriver.enabled", False)
        profile.set_preference('useAutomationExtension', False)
        profile.update_preferences()
        desired = DesiredCapabilities.FIREFOX
        cls.selenium = webdriver.Firefox(options=ff_options, firefox_profile=profile, desired_capabilities=desired)
        cls.selenium.implicitly_wait(implicitly_wait)
        """
        super(LiveServerSeleniumTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(LiveServerSeleniumTestCase, cls).tearDownClass()

    def set_current_site_domain(self):
        current_site = Site.objects.get_current()
        current_site.domain = settings.SITE_DOMAIN
        current_site.save()
        return current_site

    def take_screenshot_before_pay(self, img_name, img_dir="/tmp"):
        try:
            self.selenium.find_element(by=By.ID, value="main-content").screenshot(join(img_dir, img_name + ".png"))
        except NoSuchElementException as exc:
            if settings.DEBUG:
                print("WARNING: Screenshot not taken (%s)" % exc)

    def jsclick(self, jquery_selector):
        self.selenium.execute_script('$("%s").trigger("click")' % jquery_selector)
