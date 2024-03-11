from selenium import webdriver

# keep commented according lines to use chrome or firefox:
from selenium.webdriver.chrome.options import Options as ChromeOptions
# from selenium.webdriver.firefox.options import Options as FirefoxOptions
# from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from django.conf import settings
from django.core.servers.basehttp import ThreadedWSGIServer
from django.contrib.sites.models import Site
from django.contrib.staticfiles.testing import LiveServerTestCase
from django.test.testcases import LiveServerThread, QuietWSGIRequestHandler


class LiveServerThreadWithReuse(LiveServerThread):
    """
    This miniclass overrides _create_server to allow port reuse. This avoids creating
    "address already in use" errors for tests that have been run subsequently.
    taken from: https://stackoverflow.com/a/51756256
    """

    def _create_server(self, connections_override=True):
        return ThreadedWSGIServer((self.host, self.port), QuietWSGIRequestHandler, allow_reuse_address=True)


class LiveServerSeleniumTestCase(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        cls.host = settings.SITE_DOMAIN
        cls.port = settings.TESTING_PORT
        cls.url_scheme = settings.URL_SCHEME
        cls.server_thread_class = LiveServerThreadWithReuse
        super(LiveServerSeleniumTestCase, cls).setUpClass()
        implicitly_wait = 0.5
        headless = settings.TESTING_CHROME_HEADLESS

        # chrome setup:
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
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(implicitly_wait)
        driver.delete_all_cookies()
        cls.selenium = driver
        cls.waitsecs = getattr(settings, "SIGNUPWALL_SELENIUM_DEFAULT_WAITSECS", 30)

        # firefox setup:
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

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(LiveServerSeleniumTestCase, cls).tearDownClass()

    def set_current_site_domain(self):
        current_site = Site.objects.get_current()
        current_site.domain = settings.SITE_DOMAIN
        current_site.save()
        return current_site

    def jsclick(self, jquery_selector):
        self.selenium.execute_script('$("%s").trigger("click")' % jquery_selector)
