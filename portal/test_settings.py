from __future__ import absolute_import
from __future__ import unicode_literals
# import faulthandler

from settings import *  # noqa
from local_settings import *  # noqa


# This can be useful to debug segmentation fault errors
# faulthandler.enable()

try:
    from local_test_settings import *  # noqa
except ImportError:
    pass
