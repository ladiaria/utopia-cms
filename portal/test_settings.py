# import faulthandler

from settings import *
from local_settings import *


# This can be useful to debug segmentation fault errors
# faulthandler.enable()

try:
    from local_test_settings import *
except ImportError:
    pass
