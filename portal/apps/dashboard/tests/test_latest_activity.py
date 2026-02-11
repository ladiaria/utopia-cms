from time import sleep

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.utils import timezone

from libs.scripts.pwclear import pwclear
from core.models import Article
from core.factories import UserFactory
from ..utils import latest_activity


class LatestActivityTestCase(TestCase):
    fixtures = ['test']
    http_host_header_param = {'HTTP_HOST': settings.SITE_DOMAIN}

    def test01_no_error(self):
        start = timezone.now()
        sleep(1)  # 1 sec error tolerance for left bound
        pwclear()
        c, password, user = Client(), User.objects.make_random_password(), UserFactory()
        user.set_password(password)
        user.save()
        c.login(username=user.username, password=password)
        visit_count = 0
        for a in Article.published.iterator():
            c.get(a.get_absolute_url(), **self.http_host_header_param)
            visit_count += 1
            if visit_count == settings.SIGNUPWALL_MAX_CREDITS - 1:
                break
        sleep(1)  # 1 sec error tolerance for right bound
        end = timezone.now()
        la = latest_activity(user)
        if settings.DEBUG:
            print("LatestActivityTestCase result: %s" % la)
        self.assertGreater(la, start)
        self.assertLess(la, end)
