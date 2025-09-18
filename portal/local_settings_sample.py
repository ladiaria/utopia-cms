# -*- coding: utf-8 -*-
INTERNAL_IPS = ("127.0.0.1", "0.0.0.0", "*")
REMOTE_ADDR = "*"

DEBUG = True  # remove this line or set to False in production
TEMPLATE_DEBUG = DEBUG
REMOVE_WWW = not DEBUG
AMP_SIMULATE = True  # remove this line or set to False in production
RESTRICT_ACCESS = False
SECRET_KEY = ""  # fill with any value as described in INSTALL.md

# Site settings
SITE_DOMAIN = "yoogle.com"  # Don't use this domain in production, use a "real" one you own
SESSION_COOKIE_DOMAIN = "." + SITE_DOMAIN
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN]

COMPRESS_OFFLINE = not DEBUG
COMPRESS_ENABLED = True
KEY_PREFIX = SITE_DOMAIN  # see: https://docs.djangoproject.com/en/4.1/ref/settings/#key-prefix

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

CRM_API_BASE_URI = 'http://localhost:8000/api/'

# IPFS
# The web3.storage API Token used to upload files to the web3.storage service.
# To generate an API Token with your account, refer to the following URL:
# https://web3.storage/docs/how-tos/generate-api-token/
# IPFS_TOKEN = ""

# Set to True to use Google One Tap and forward login_hint, or False to use the default Google OAuth2 backend.
ENABLE_GOOGLE_ONE_TAP = False

# Add GIGAN to subscription types
THEDAILY_SUBSCRIPTION_TYPE_CHOICES = (
    ('DDIGM', 'Suscripción digital'),
    ('DDIGMFS', 'Suscripción digital + Fin de semana'),
    ('PAPYDIM', 'Suscripción papel'),
    ('LDFS', 'la diaria fin de semana'),
    ('PAPYLAS', 'la diaria lunes a sábados'),
    ('LENM', 'Revista Lento'),
    ('LEMONDE', 'Le Monde diplomatique'),
    ('GIGAN', 'Gigantes'),  # Children's magazine

)


# SMS Registration Settings
THEDAILY_SMS_MAX_SEND_ATTEMPTS = 5          # Maximum SMS send attempts per email/phone
THEDAILY_SMS_MAX_VERIFY_ATTEMPTS = 5        # Maximum code verification attempts per code
THEDAILY_SMS_COOLDOWN_SECONDS = 30          # Seconds to wait between SMS sends
THEDAILY_SMS_AUTO_RESET_HOURS = 1           # Hours after which attempt counters reset automatically (0 to disable)
THEDAILY_SMS_CODE_EXPIRY_MINUTES = 2        # Minutes after which SMS code expires

# SMS Service Configuration (utopia_cms_ladiaria)
SMS_USE_MOCK = False                        # Set to True for development, False for production
SMS_API_KEY = 'CRM key here'                # Use same API key as CRM
SMS_BASE_URL = 'http://localhost:8000'      # CRM base URL (without /api/)
SMS_TIMEOUT = 30                            # Request timeout in seconds
SMS_BASE_URL = CRM_API_BASE_URI      # CRM base URL (without /api/)
SMS_TIMEOUT = 30                            # Request timeout in seconds
