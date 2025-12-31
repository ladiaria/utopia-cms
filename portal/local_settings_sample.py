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
TWILIO_AUTH_TOKEN = ''         # Your Twilio Auth Token (keep secret!)
TWILIO_FROM_NUMBER = ''        # Your Twilio phone number (e.g., '+1234567890')

# CORS Configuration (django-cors-headers)
# Configure Cross-Origin Resource Sharing to allow some cool dev tools you're using to access resources on this server.
# IMPORTANT: Only add trusted domains to prevent unauthorized access.
#
# For example, for development in localhost:
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",      # Next.js development server
#     "http://127.0.0.1:3000",      # Alternative localhost
# ]

# Allow credentials (cookies, authorization headers) to be sent in CORS requests.
# Required for HttpOnly cookie-based refresh tokens.
# CORS_ALLOW_CREDENTIALS = True

# Cross-Domain Redirects Configuration
# Allow redirects to specific domains after login/logout (for SSO)
# This is required for:
# 1. Google OAuth login redirects to external domains
# 2. Login/logout with ?next=https://external-domain parameter
#
# Security: Only add trusted domains you control, examples:
# ALLOWED_REDIRECT_HOSTS = [
#     'crm.yoogle.com',      # utopia-CRM sibling paired with this utopia-cms
#     'comments.yoogle.com', # Coral talk site used by articles paired with this utopia-cms
# ]

# Signupwall Configuration
# Enable landing page for X in-app browser to guide users to open articles in external browser
# This solves the "Access blocked" error when users try to login with Google from X's in-app browser
# Set to True to enable the feature, False to disable it
# SIGNUPWALL_X_BROWSERWALL_ENABLED = True


# =============================================================================
# Sentry Error Tracking Configuration
# =============================================================================
# Sentry captures and reports errors/exceptions to help with debugging and monitoring.
# Get your DSN from: https://sentry.io/settings/projects/
#
# Enable/disable Sentry error tracking
# SENTRY_ENABLED = True  # Set to False to disable Sentry completely
#
# Sentry DSN (Data Source Name) - KEEP THIS SECRET!
# Get this from your Sentry project settings: https://sentry.io/settings/[your-org]/projects/[your-project]/keys/
# SENTRY_DSN = "https://YOUR_KEY@YOUR_SENTRY_INSTANCE.ingest.sentry.io/YOUR_PROJECT_ID"
#
# Environment name (for separating errors in Sentry dashboard)
# Auto-detects based on DEBUG and SITE_DOMAIN:
#   - DEBUG=True → "development"
#   - "piques.uy" in domain → "piques" (staging/testing environment)
#   - Otherwise → "production"
#
# You can override this by setting:
# SENTRY_ENVIRONMENT = "staging"  # or "development", "production", etc.
#
# Example configuration (uncomment and fill in your DSN):
# if DEBUG:
#     SENTRY_ENVIRONMENT = "development"
# elif "piques.uy" in SITE_DOMAIN:  # or your testing domain
#     SENTRY_ENVIRONMENT = "piques"
# else:
#     SENTRY_ENVIRONMENT = "production"
#
# if SENTRY_ENABLED and SENTRY_DSN:
#     import sentry_sdk
#     from sentry_sdk.integrations.django import DjangoIntegration
#     import os
#
#     def before_send(event, hint):
#         """Hook to filter/modify events before sending to Sentry."""
#         # Filter out events from bots/crawlers
#         request = event.get('request', {})
#         user_agent = request.get('headers', {}).get('User-Agent', '')
#         bot_patterns = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget']
#         if any(pattern in user_agent.lower() for pattern in bot_patterns):
#             return None  # Don't send to Sentry
#
#         # Remove sensitive data from request body/headers
#         if 'request' in event and 'data' in event['request']:
#             sensitive_keys = ['password', 'token', 'secret', 'api_key', 'credit_card']
#             for key in sensitive_keys:
#                 if key in event['request']['data']:
#                     event['request']['data'][key] = '[Filtered]'
#         return event
#
#     sentry_sdk.init(
#         dsn=SENTRY_DSN,
#         integrations=[DjangoIntegration()],
#
#         # Hook to filter/modify events before sending
#         before_send=before_send,
#
#         # Environment (dev/piques/production) for filtering errors in Sentry dashboard
#         environment=SENTRY_ENVIRONMENT,
#
#         # Release tracking: Links errors to specific git commits for easier debugging.
#         # To enable this feature, set GIT_COMMIT environment variable before starting Django:
#         #   export GIT_COMMIT=$(git rev-parse --short HEAD)
#         # Without it, all errors will show release="utopia-cms@unknown"
#         # release=f"utopia-cms@{os.getenv('GIT_COMMIT', 'unknown')}",
#
#         # Performance monitoring: 0.0 = disabled (Phase 1), 1.0 = track all requests
#         traces_sample_rate=0.0,
#
#         # Send user context automatically: IP address, user agent, HTTP headers, cookies
#         # Note: This is separate from SentryUserContextMiddleware which adds email, username, subscription info
#         send_default_pii=True,
#
#         # Ignore expected errors that should not be reported to Sentry
#         ignore_errors=[
#             KeyboardInterrupt,
#             # Django common errors that are not bugs
#             'django.core.exceptions.DisallowedHost',  # Invalid HOST header
#             'django.http.Http404',  # 404s are expected, not errors
#             # Network/Connection errors (client-side issues, not server bugs)
#             'BrokenPipeError',  # Client closed connection
#             'ConnectionResetError',  # Network reset
#             'ConnectionAbortedError',  # Connection aborted
#             'RemoteDisconnected',  # HTTP client disconnected
#             # Cloudflare errors (CDN/proxy issues, not application bugs)
#             'CloudFlareError',
#             'CloudflareError',
#         ],
#     )
#
# =============================================================================
# End of Sentry Configuration
# =============================================================================

# =============================================================================
# Django Admin Locking Configuration
# =============================================================================
# Prevents concurrent editing conflicts in Django Admin by locking pages when
# a user is editing them. When another user tries to edit the same object,
# they see a warning banner and all fields are disabled (read-only).
#
# This solves "Lost Update" race conditions where changes from one user
# overwrite changes from another user editing the same object simultaneously.
#
# Example:
#   - User A opens an Article → Can edit (lock acquired)
#   - User B opens same Article → Sees "⚠️ This page is being edited by User A"
#   - User B's fields are read-only until User A finishes or lock expires
#
# Repository: https://github.com/jonasundderwolf/django-admin-locking
#
# ADMIN_PAGE_LOCK_ENABLED = True
#
# Add django-admin-locking to INSTALLED_APPS
# INSTALLED_APPS += ('admin_locking',)
#
# Lock timeout in minutes (default: 15)
# After this time of inactivity, locks expire and another user can edit
# Note: While a page is open, the lock is automatically renewed every 10 seconds
# ADMIN_LOCKING_TIMEOUT = 10
#
# Requirements:
#   - Redis or Memcached must be running (uses Django's default cache)
#   - Add to requirements.txt: django-admin-locking==0.10.0
#
# Performance impact:
#   - Each user with an open edit page sends 6 requests/minute (1 every 10s)
#   - Negligible load: ~10ms per request (Redis GET + SET)
#   - Example: 50 concurrent editors = 300 requests/min = insignificant CPU usage
#
# =============================================================================
# End of Django Admin Locking Configuration
# =============================================================================
