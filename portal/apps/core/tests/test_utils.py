# coding:utf-8
from django.test import TestCase

from ..utils import get_app_template


class UtilsTestCase(TestCase):
    targets = []

    def test_get_app_template(self):
        for relative_path, result_path in self.targets:
            self.assertEqual(get_app_template(relative_path), result_path)
