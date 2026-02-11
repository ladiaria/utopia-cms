# coding=utf-8
from settings import *  # noqa


try:
    from local_ci_test_settings import *  # noqa
except ImportError:
    pass
