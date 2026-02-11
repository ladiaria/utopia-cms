# coding=utf-8
from test_settings import *  # noqa


try:
    from local_test_settings import *  # noqa
except ImportError:
    pass


# use the test databse
DATABASES['default']['NAME'] = 'test_' + DATABASES['default']['NAME']  # noqa
