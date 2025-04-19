from settings import *  # noqa


# next line can be useful to debug segmentation fault errors:
# import faulthandler; faulthandler.enable()

AMP_SIMULATE = True  # Tests will allways run "locally", then this variable must be True

# TODO: migrate this to a fixture
# THEDAILY_SUBSCRIPTION_TYPE_DEPRECATEDCHOICES = (
#     ("DDIGM", "Suscripción digital"),
#     ("PAPYDIM", "Suscripción papel"),
#     ("spinoff", "Suscripción digital spinoff"),
# )

if not locals().get("THEDAILY_CURRENCY_CHOICES"):
    print("NOTE: filling THEDAILY_CURRENCY_CHOICES with some default values for testing purposes")
    THEDAILY_CURRENCY_CHOICES = (
        ("UYU", "Peso uruguayo"),
        ("ARS", "Peso argentino"),
        ("BRL", "Real brasilero"),
        ("CLP", "Peso chileno"),
        ("MXN", "Peso mexicano"),
        ("COP", "Peso colombiano"),
        ("PEN", "Sol peruano"),
    )
if not locals().get("THEDAILY_CURRENCY_CHOICES_DEFAULT"):
    THEDAILY_CURRENCY_CHOICES_DEFAULT = THEDAILY_CURRENCY_CHOICES[0][0]
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
