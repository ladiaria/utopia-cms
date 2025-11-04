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
SMS_BASE_URL = CRM_API_BASE_URI      # CRM base URL (without /api/)
SMS_TIMEOUT = 30                            # Request timeout in seconds

# SMS Smart Routing Configuration
# When enabled, configured country codes use CRM SMS service, others use Twilio
SMS_USE_SMART_ROUTING = True                       # Set to True to enable smart routing

# Country codes that use CRM SMS service (when smart routing is enabled)
# Dictionary: {country_code: country_name} - codes WITHOUT the + prefix
SMS_CRM_COUNTRY_CODES = {
    '54': 'Argentina',
    '55': 'Brasil',
    '56': 'Chile',
    '598': 'Uruguay',
    '1': 'USA/Canada',
}

# Twilio Configuration (for international SMS when smart routing is enabled)
# Get these credentials from: https://console.twilio.com/
TWILIO_ACCOUNT_SID = ''        # Your Twilio Account SID (e.g., 'ACxxxxx...')
TWILIO_AUTH_TOKEN = ''           # Your Twilio Auth Token (keep secret!)
TWILIO_FROM_NUMBER = ''                              # Your Twilio phone number (e.g., '+1234567890')

# =============================================================================
# JWT Authentication Configuration (djangorestframework-simplejwt)
# =============================================================================
# Enable JWT authentication for REST API (consumed by external clients like Next.js apps)
# Set to True to enable, False to disable.
JWT_ENABLED = True

# IMPORTANT: After enabling JWT_ENABLED for the first time, run migrations:
#   python manage.py migrate token_blacklist
#
# Configuration for JWT tokens (only used if JWT_ENABLED=True)
from datetime import timedelta

SIMPLE_JWT = {
    # Token Lifetimes
    # ---------------
    # Access token: Short-lived token sent in Authorization header for each API request.
    # Recommended: 15 minutes (modern security standard).
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),

    # Refresh token: Long-lived token used to obtain new access tokens when they expire.
    # Stored as HttpOnly cookie (not accessible by JavaScript for security).
    # Recommended: 7 days.
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),

    # Token Rotation (Security Feature)
    # ----------------------------------
    # When True: Each time a refresh token is used, a NEW refresh token is generated
    # and the old one is invalidated. This prevents token reuse attacks.
    'ROTATE_REFRESH_TOKENS': True,

    # When True: Old refresh tokens are added to a blacklist after rotation,
    # preventing their reuse even if stolen. Requires the token_blacklist app.
    'BLACKLIST_AFTER_ROTATION': True,

    # Algorithm and Signing
    # ---------------------
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': None,  # Uses settings.SECRET_KEY by default

    # Token Headers
    # -------------
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    # Custom Serializers
    # ------------------
    # Override to add custom claims (e.g., is_subscriber, email, name)
    'TOKEN_OBTAIN_SERIALIZER': 'utopia_cms_radio.serializers.CustomTokenObtainPairSerializer',

    # User Identification
    # -------------------
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # Token Types
    # -----------
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# =============================================================================
# CORS Configuration (django-cors-headers)
# =============================================================================
# Configure Cross-Origin Resource Sharing to allow API requests from your Next.js frontend.
# IMPORTANT: Only add trusted domains to prevent unauthorized access.
#
# For development (localhost):
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",      # Next.js development server
    "http://127.0.0.1:3000",      # Alternative localhost
]

# For production, add your actual frontend domains:
# CORS_ALLOWED_ORIGINS = [
#     "https://radio.ladiaria.com.uy",  # Production
#     "https://radio.piques.uy",         # Staging
# ]

# Allow credentials (cookies, authorization headers) to be sent in CORS requests.
# Required for HttpOnly cookie-based refresh tokens.
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# API Documentation Configuration (drf-spectacular)
# =============================================================================
# Enable API documentation endpoints (Swagger UI, ReDoc, OpenAPI schema)
# Set to True in development/test environments, False in production for security.
# URLs: /api/docs/ (Swagger), /api/redoc/ (ReDoc), /api/schema/ (OpenAPI JSON)
UTOPIA_CMS_RADIO_API_DOCS_ENABLED = True  # Set to False in production

# Optionally, allow specific HTTP methods:
# CORS_ALLOW_METHODS = [
#     'DELETE',
#     'GET',
#     'OPTIONS',
#     'PATCH',
#     'POST',
#     'PUT',
# ]

# Optionally, allow specific headers:
# CORS_ALLOW_HEADERS = [
#     'accept',
#     'accept-encoding',
#     'authorization',
#     'content-type',
#     'dnt',
#     'origin',
#     'user-agent',
#     'x-csrftoken',
#     'x-requested-with',
# ]

# =============================================================================
# SSO Configuration - Share cookies between domains
# =============================================================================
# This enables Single Sign-On (SSO) between the main Django site and external apps
# Users authenticated in one site will automatically be authenticated in the other
#
# For local development, SESSION_COOKIE_DOMAIN is usually set earlier in this file.
# For production, override it here to share cookies across subdomains:
#
# Production examples:
# SESSION_COOKIE_DOMAIN = '.ladiaria.com.uy'  # Shares across *.ladiaria.com.uy
# SESSION_COOKIE_DOMAIN = '.piques.uy'         # Shares across *.piques.uy (staging)
#
# Cookie security settings (adjust based on DEBUG mode):
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True

# =============================================================================
# End of JWT Authentication Configuration
# =============================================================================