# coding=utf-8
from ci_test_settings import *  # noqa


# use the test databse
DATABASES['default']['NAME'] = 'test_' + DATABASES['default']['NAME']  # noqa
