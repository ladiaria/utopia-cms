# -*- coding: utf-8 -*-
from settings import INSTALLED_APPS, MIDDLEWARE


INTERNAL_IPS = ("127.0.0.1", "0.0.0.0", "*")
REMOTE_ADDR = "*"

DEBUG = True  # remove this line or set to False in production
TEMPLATE_DEBUG = DEBUG
REMOVE_WWW = not DEBUG
AMP_SIMULATE = True  # remove this line or set to False in production
RESTRICT_ACCESS = False
SECRET_KEY = ""  # fill with any value as described in INSTALL.md

if DEBUG:
    MIDDLEWARE = list(MIDDLEWARE)
    MIDDLEWARE.insert(5, "corsheaders.middleware.CorsMiddleware")
    MIDDLEWARE = tuple(MIDDLEWARE)

# Site settings
CLOSED_SITE = False  # TODO: this feature should be reviewed (its middlewares are not ready for this Django version.
SITE_DOMAIN = "yoogle.com"  # Don't use this domain in production, use a "real" one you own
SESSION_COOKIE_DOMAIN = "." + SITE_DOMAIN
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN]

COMPRESS_OFFLINE = not DEBUG
COMPRESS_ENABLED = True
KEY_PREFIX = SITE_DOMAIN  # see: https://docs.djangoproject.com/en/4.1/ref/settings/#key-prefix

if CLOSED_SITE or RESTRICT_ACCESS:
    INSTALLED_APPS += ("closed_site",)
    MIDDLEWARE = (
        "closed_site.middleware.ClosedSiteMiddleware",
        "closed_site.middleware.RestrictedAccessMiddleware",
    ) + MIDDLEWARE

ADMINS = (("Admin", "admin@example.com"),)  # change to a real mailbox for non-dev deployments

MANAGERS = ADMINS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "utopiacms",
        "USER": "utopiacms_user",
        "PASSWORD": "password",
        "OPTIONS": {"init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
    }
}

# example of custom datetime formatting
TIME_ZONE = "America/Montevideo"
DATE_FORMAT = "l j de F de Y"
TIME_FORMAT = "H:i:s"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"
SHORT_DATE_FORMAT = "d/m/Y"

# Uncomment this next 2 settings to "force-off" the dark mode UI in django admin (even if your browser is dark-moded).
# TODO: document this problem/solution
# PORTAL_ADMIN_DARK_MODE_VARS_TEMPLATE = "admin/admin_dark_mode_vars_template_empty.html"
# PORTAL_ADMIN_CHANGE_FORM_MARTOR_CUSTOM_CSS = "css/admin_dark_mode_revert_martor.css"

# email
EMAIL_SUBJECT_PREFIX = "[cms] "
DEFAULT_FROM_EMAIL = "cms dev <cms@example.com>"  # change to a real mailbox for non-dev deployments
EMAIL_HOST = "localhost"
EMAIL_PORT = 2500

SERVER_EMAIL = DEFAULT_FROM_EMAIL

SENDNEWSLETTER_LOGFILE = "/home/user/utopia-cms-data/sendnewsletter/%s-%s.log"

EMAIL_EDITION_NUMBER_OFFSET = 0

# Social auth for a local dev server
USE_X_FORWARDED_HOST = True
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

# Google tag manager
GTM_CONTAINER_ID = ""
GTM_AMP_CONTAINER_ID = ""
GA_MEASUREMENT_ID = ""

# Recaptcha
RECAPTCHA_PUBLIC_KEY = ""
RECAPTCHA_PRIVATE_KEY = ""
THEDAILY_SUBSCRIPTION_CAPTCHA_DEFAULT_COUNTRY = ""  # 2-char (in caps) country iso code
THEDAILY_SUBSCRIPTION_CAPTCHA_COUNTRIES_IGNORED = [THEDAILY_SUBSCRIPTION_CAPTCHA_DEFAULT_COUNTRY]

# IPFS
# The web3.storage API Token used to upload files to the web3.storage service.
# To generate an API Token with your account, refer to the following URL:
# https://web3.storage/docs/how-tos/generate-api-token/
# IPFS_TOKEN = ""
