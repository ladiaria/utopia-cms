from settings import *  # noqa


# This can be useful to debug segmentation fault errors:
# import faulthandler; faulthandler.enable()


THEDAILY_SUBSCRIPTION_TYPE_CHOICES = {
    "DDIGM": "Suscripción digital",
    "PAPYDIM": "Suscripción papel",
}

try:
    from local_test_settings import *  # noqa
except ImportError:
    if DEBUG:  # noqa
        print("WARNING: local_test_settings import is rising error")
