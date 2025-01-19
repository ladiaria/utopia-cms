from settings import *  # noqa


# This can be useful to debug segmentation fault errors:
# import faulthandler; faulthandler.enable()


if not locals().get("THEDAILY_SUBSCRIPTION_TYPE_CHOICES"):
    print("NOTE: filling THEDAILY_SUBSCRIPTION_TYPE_CHOICES with some default values for testing purposes")
    THEDAILY_SUBSCRIPTION_TYPE_CHOICES = (
        ("DDIGM", "Suscripción digital"),
        ("PAPYDIM", "Suscripción papel"),
        ("spinoff", "Suscripción digital spinoff"),
    )


if not locals().get("THEDAILY_SUBSCRIPTION_TYPE_DEFAULT"):
    THEDAILY_SUBSCRIPTION_TYPE_DEFAULT = THEDAILY_SUBSCRIPTION_TYPE_CHOICES[0][0]


if not locals().get("THEDAILY_PROVINCE_CHOICES"):
    print("NOTE: filling THEDAILY_PROVINCE_CHOICES with some default values for testing purposes")
    THEDAILY_PROVINCE_CHOICES = (
        ("", ""),
        ("Montevideo", "Montevideo"),
    )


try:
    from local_test_settings import *  # noqa
except ImportError:
    if DEBUG:  # noqa
        print("WARNING: local_test_settings import is rising error")
