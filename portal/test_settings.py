from settings import *  # noqa


# This can be useful to debug segmentation fault errors:
# import faulthandler; faulthandler.enable()


if not locals().get("THEDAILY_SUBSCRIPTION_TYPE_CHOICES"):
    THEDAILY_SUBSCRIPTION_TYPE_CHOICES = (
        ("DDIGM", "Suscripción digital"),
        ("PAPYDIM", "Suscripción papel"),
    )
if not locals().get("THEDAILY_PROVINCE_CHOICES"):
    THEDAILY_PROVINCE_CHOICES = (
        ("", ""),
        ("Montevideo", "Montevideo"),
    )

if not locals().get("THEDAILY_SUBSCRIPTION_TYPE_DEFAULT"):
    THEDAILY_SUBSCRIPTION_TYPE_DEFAULT = THEDAILY_SUBSCRIPTION_TYPE_CHOICES[0][0]


try:
    from local_test_settings import *  # noqa
except ImportError:
    if DEBUG:  # noqa
        print("WARNING: local_test_settings import is rising error")
