# -*- coding: utf-8 -*-
import sys
from os.path import abspath, basename, dirname, join, realpath
import mimetypes
from freezegun import freeze_time
from kombu import Queue

import django
from django.conf.global_settings import DEFAULT_CHARSET
from django.contrib.messages import constants as messages
from django.utils.encoding import smart_str, force_str


# this fix an error with smart_text on some apps (django-tagging)
django.utils.encoding.smart_text = smart_str
django.utils.encoding.force_text = force_str

PROJECT_ABSOLUTE_DIR = dirname(abspath(__file__))
PROJECT_NAME = basename(PROJECT_ABSOLUTE_DIR)
APPS_DIR = join(PROJECT_ABSOLUTE_DIR, "apps")
if APPS_DIR not in sys.path:
    sys.path.insert(0, APPS_DIR)

SITE_ROOT = dirname(realpath(__file__))
STATIC_URL = "/static/"
STATIC_ROOT = f"{SITE_ROOT}/static/"
STATICFILES_DIRS = (join(SITE_ROOT, "../static/"),)
SITE_DOMAIN = "example.com"
URL_SCHEME = "https"
DEFAULT_URL_SCHEME = URL_SCHEME
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# default filename for the bse_template used to extend by variable
PORTAL_BASE_TEMPLATE = "base.html"
# country name in page titles
PORTAL_TITLE_APPEND_COUNTRY = True

# disable template settings warning until fixed migrating django-mobile to django-amp-tools
SILENCED_SYSTEM_CHECKS = ["1_8.W001"]

# django-amp-tools
AMP_TOOLS_GET_PARAMETER = "display"

# Multi sub-domain secure cookie
SESSION_COOKIE_DOMAIN = "." + SITE_DOMAIN
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_AGE = 2592000  # 30 days
CSRF_COOKIE_SECURE = True
SESSION_SERIALIZER = "django.contrib.sessions.serializers.PickleSerializer"

AMP_DEBUG = False
RAW_SQL_DEBUG = False

STATICFILES_FINDERS = (
    "compressor.finders.CompressorFinder",
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

INSTALLED_APPS = (
    "amp_tools",
    "django.contrib.staticfiles",
    "admin_shortcuts",
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sitemaps",
    "django.contrib.sites",
    "django.contrib.redirects",
    "audiologue",
    "tagging",
    "core.config.CoreConfig",
    "core.attachments",
    "groupedtags.config.GroupedTagsConfig",
    "django_extensions",
    "generator",
    "shoutbox",
    "thedaily",
    "videologue",
    "short",
    "adzone",
    "exchange",
    "faq",
    "django_recaptcha",
    "photologue",
    "sortedm2m",
    "photologue_ladiaria",
    "robots",
    "search",
    "django_elasticsearch_dsl",
    "sorl.thumbnail",
    "shorturls",
    "less",
    "django_user_agents",
    "updown",
    "crispy_forms",
    "crispy_forms_materialize",
    "actstream",
    "django.contrib.messages",
    "signupwall",
    "homev3",
    "cartelera.config.CarteleraConfig",
    "martor",
    "django_bleach",
    "comunidad",
    "star_ratings",
    "tagging_autocomplete_tagit",
    "avatar",
    "notification",
    "django.contrib.flatpages",
    "epubparser",
    "django_filters",
    "rest_framework",
    "rest_framework.authtoken",
    "dashboard",  # placed after authtoken to unregister TokenAdmin and register a fixed version of it
    "rest_framework_api_key",
    "compressor",
    "favit",
    "social_django",
    "django_amp_readerid.apps.DjangoAmpReaderidConfig",
    "reversion",
    "django_celery_results",
    "django_celery_beat",
    "phonenumber_field",
    "closed_site",
)

SITE_ID = 1

# martor
# disable emoji (our markdown filter not yet support this)
MARTOR_TOOLBAR_BUTTONS = [
    "bold",
    "italic",
    "horizontal",
    "heading",
    "pre-code",
    "blockquote",
    "unordered-list",
    "ordered-list",
    "link",
    "image-link",
    "image-upload",
    "direct-mention",
    "toggle-maximize",
    "help",
]
MARTOR_ENABLE_LABEL = True  # enable field labels

# photologue app need to add a custom migration
MIGRATION_MODULES = {"photologue": "photologue_ladiaria.photologue_migrations"}

ADMIN_SHORTCUTS = [
    {
        "title": "Links directos (edición)",
        "shortcuts": [
            {"url_name": "admin:core_publication_changelist", "title": "Publicaciones", "icon": "newspaper"},
            {"url_name": "admin:core_edition_changelist", "title": "Ediciones", "icon": "newspaper"},
            {"url_name": "admin:core_edition_add", "title": "Crear edición"},
            {"url_name": "admin:core_article_add", "title": "Crear Artículo"},
        ],
    },
    {
        "title": "Reportes y otras utilidades",
        "shortcuts": [{"url": "/dashboard/", "title": 'Reportes, estadísticas y "previews"', "icon": "chart-line"}],
    },
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAdminUser",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
}

ACTSTREAM_SETTINGS = {"FETCH_RELATIONS": False, "USE_PREFETCH": True}

CRISPY_ALLOWED_TEMPLATE_PACKS = ("bootstrap", "uni_form", "bootstrap3", "bootstrap4", "materialize_css_forms")
CRISPY_TEMPLATE_PACK = "materialize_css_forms"

MIDDLEWARE = (
    "closed_site.middleware.ClosedSiteMiddleware",
    "closed_site.middleware.RestrictedAccessMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.cache.UpdateCacheMiddleware",  # runs during the response phase (top -> last)
    "core.middleware.cache.AnonymousResponse",  # hacks cookie header for anon users (resp phase)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "libs.middleware.url.UrlMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.RemoteUserMiddleware",
    "django.contrib.admindocs.middleware.XViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_user_agents.middleware.UserAgentMiddleware",
    "signupwall.middleware.SignupwallMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    "core.middleware.cache.AnonymousRequest",  # hacks cookie header for anon users (req phase)
    "django.middleware.cache.FetchFromCacheMiddleware",  # runs during the request phase (top -> first)
    "social_django.middleware.SocialAuthExceptionMiddleware",
    "django.contrib.redirects.middleware.RedirectFallbackMiddleware",
)

# Localization default settings
LANGUAGES = (("en", "English"),)
USE_I18N = True
USE_L10N = True

LANGUAGE_CODE = "en"
LOCAL_LANG = "en"
LOCAL_COUNTRY = "US"

USE_TZ = True
DATE_INPUT_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",  # 2006-10-25, 25/10/2006, 25/10/06
)
DATETIME_FORMAT = "j N, Y, P"
DATETIME_INPUT_FORMATS = ("%d/%m/%Y %H:%M",)  # '10/25/2006 14:30:59'

ROOT_URLCONF = "urls"

DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000

# Default publication slug.
DEFAULT_PUB = "default"

FIRST_DAY_OF_WEEK = 0  # 0 is Sunday
# Convert to calendar module, where 0 is Monday:
FIRST_DAY_OF_WEEK_CAL = (FIRST_DAY_OF_WEEK - 1) % 7

HOME_PUBLICATIONS = []

HASHIDS_SALT = "top_secret_salt_phrase"
USER_HASHID_SALT = "top_secret_salt_phrase_for_users_ids_only"

# MEDIA
MEDIA_ROOT = PROJECT_ABSOLUTE_DIR + "/media/"
MEDIA_URL = "/media/"
ADMIN_MEDIA_PREFIX = "/media/admin/"

CSS_URL = f"{MEDIA_URL}css/"
IMG_URL = f"{MEDIA_URL}img/"
JS_URL = f"{MEDIA_URL}js/"
SWF_URL = f"{MEDIA_URL}swf/"

mimetypes.add_type("image/svg+xml", ".svg", True)
mimetypes.add_type("image/svg+xml", ".svgz", True)

# AVATAR
AVATAR_DEFAULT_IMAGE = "identicon"

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache", "LOCATION": ["127.0.0.1:11211"]}
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [join(PROJECT_ABSOLUTE_DIR, "templates"), join(PROJECT_ABSOLUTE_DIR, "apps")],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "context_processors.urls",
                "context_processors.site",
                "context_processors.publications",
                "context_processors.gtm",
                "context_processors.main_menus",
                "context_processors.article_content_type",
                "django.template.context_processors.static",
                "apps.core.context_processors.aniosdias",
                "apps.core.context_processors.bn_module",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.tz",
                "adzone.context_processors.get_source_ip",
                "apps.thedaily.context_processors.permissions",
                "django.template.context_processors.csrf",
            ],
            "loaders": [
                "amp_tools.loader.Loader",
                (
                    "django.template.loaders.cached.Loader",
                    ["django.template.loaders.filesystem.Loader", "django.template.loaders.app_directories.Loader"],
                ),
            ],
        },
    }
]

FIXTURE_DIRS = (join(PROJECT_ABSOLUTE_DIR, "fixtures"),)

# EMAIL
EMAIL_FAIL_SILENTLY = False

NOTIFICATIONS_FROM_NAME = "utopia cms"
NOTIFICATIONS_FROM_ADDR1 = "suscriptores@example.com"
NOTIFICATIONS_FROM_ADDR2 = "ventas@example.com"
NOTIFICATIONS_TO_NAME = "Suscripciones"
NOTIFICATIONS_TO_ADDR = "suscripciones@example.com"
NOTIFICATIONS_FROM_MX = NOTIFICATIONS_FROM_ADDR1
NEWSLETTERS_FROM_MX = NOTIFICATIONS_FROM_MX

NEWSLETTER_IMG_FORMAT = "jpg"

SENDNEWSLETTER_EXPORT_DIR = "/var/local/utopiacms/sendnewsletter_export"
SENDNEWSLETTER_LOGFILE = "/var/log/utopiacms/sendnewsletter/%s-%s.log"

# celery
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
"""
With the following set of queues, 3 workers are started to process the 3 different queues, upd_* is meant to be used in
a worker with only one process (concurrency 1), and the concurrent_tasks queue can be used with any concurrency, those
3 workers can be started executing the following commands, also a .ini sample conf for supervisor is provided inside
the "docs" directory in the root of the project. In portal directory, in a different shell for each command, run:

$ DJANGO_SETTINGS_MODULE=settings celery -A apps.celeryapp worker -Q upd_category_home -c 1 -l INFO -n utopiacms_w1@%h
$ DJANGO_SETTINGS_MODULE=settings celery -A apps.celeryapp worker -Q upd_articles_url -c 1 -l INFO -n utopiacms_w2@%h
$ DJANGO_SETTINGS_MODULE=settings celery -A apps.celeryapp worker -Q concurrent_tasks -c 2 -l INFO -n utopiacms_w3@%h

If you want to use/test celery-beat, you also need a worker for it which can be started this way:

$ DJANGO_SETTINGS_MODULE=settings celery -A apps.celeryapp beat -l INFO

NOTE: The provided sample supervisor conf file uses a "run" directory to store the worker's main process PIDs, needed
      to restart them gracefully sending a TERM signal, read more about this in this two sections of the celery docs:
      - https://docs.celeryq.dev/en/latest/userguide/workers.html#stopping-the-worker
      - https://docs.celeryq.dev/en/latest/userguide/workers.html#restarting-the-worker
"""
CELERY_QUEUES = {
    "upd_category_home": {"exchange": "upd_category_home", "binding_key": "upd_category_home"},
    "upd_articles_url": {"exchange": "upd_articles_url", "binding_key": "upd_articles_url"},
    "concurrent_tasks": {"exchange": "concurrent_tasks", "binding_key": "concurrent_tasks"},
}
CELERY_TASK_ROUTES = {
    "update-category-home": {"queue": "upd_category_home"},
    "update-article-urls": {"queue": "upd_articles_url"},
    "send-push-notification": {"queue": "concurrent_tasks"},
}
CELERY_TASK_QUEUES = []  # will be populated after local settings imports
CELERY_RESULT_EXTENDED = True

# Elasticsearch is disabled by default, to enable it you need to adjust this settings according to your Elasticsearch
# installation, see https://django-elasticsearch-dsl.readthedocs.io/en/latest/quickstart.html#install-and-configure
ELASTICSEARCH_DSL = {}
ELASTICSEARCH_DSL_AUTOSYNC = False
SEARCH_ELASTIC_MATCH_PHRASE = False
SEARCH_ELASTIC_USE_FUZZY = False  # Ignored when previous setting is True (not allowed by Elasticsearch).

# mongodb database
MONGODB_DATABASE = "utopia_cms"
MONGODB_NOTIMEOUT_CURSORS_ALLOWED = True

# apps

# core
# publications that use the root url as their home page
CORE_PUBLICATIONS_USE_ROOT_URL = [DEFAULT_PUB]

# slugs of the categories to update their modules after some modifications
CORE_UPDATE_CATEGORY_HOMES = []

# log user visits, disbale on critical performance issues
CORE_LOG_ARTICLE_VIEWS = True

# Article types
CORE_PHOTO_ARTICLE = "PA"
CORE_HTML_ARTICLE = "HT"
CORE_COMUNIDAD_ARTICLE = "CM"
CORE_ARTICLE_TYPES = (
    ("NE", "Noticia"),
    ("OP", "Opinión"),
    (CORE_PHOTO_ARTICLE, "Fotografía"),
    (CORE_HTML_ARTICLE, "HTML"),
    (CORE_COMUNIDAD_ARTICLE, "COMUNIDAD"),
)
# Supplement names
CORE_SUPPLEMENT_NAME_CHOICES = ()

# shows "ago" timedeltas in article cards
CORE_ARTICLE_CARDS_DATE_PUBLISHED_USE_AGO = True
# shows a date tooltip in article detail, override to False to disable the tooltip
CORE_ARTICLE_DETAIL_DATE_TOOLTIP = True
# shows the date tooltip in article detail for all dates (if prevoius setting is enabled)
# override to False to show the tooltip only since "Yesterday" dates
CORE_ARTICLE_DETAIL_ALL_DATE_TOOLTIP = True

# show or hide photo credits in article cards
CORE_ARTICLE_ENABLE_PHOTO_BYLINE = True

# class to use for the body field in articles
CORE_ARTICLE_BODY_FIELD_CLASS = "martor.models.MartorField"

# use job to build journalist absolute url
CORE_JOURNALIST_GET_ABSOLUTE_URL_USE_JOB = True

# enable related articles in article detail
CORE_ENABLE_RELATED_ARTICLES = True


SIGNUPWALL_MAX_CREDITS = 10
SIGNUPWALL_ANON_MAX_CREDITS = 0
SIGNUPWALL_RISE_REDIRECT = True
SIGNUPWALL_LABEL_EXCLUSIVE = "Exclusivo para suscripción digital de pago"

# thedaily
SUBSCRIPTION_EMAIL_SUBJECT = "Nueva suscripción"
PROMO_EMAIL_SUBJECT = "Nueva promoción"
SUBSCRIPTION_EMAIL_TO = [NOTIFICATIONS_TO_ADDR]
SUBSCRIPTION_BY_PHONE_EMAIL_TO = SUBSCRIPTION_EMAIL_TO
MAX_USERS_API_SESSIONS = 3
THEDAILY_GOOGLE_OAUTH2_ASK_PHONE = False
THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID = None
THEDAILY_SUBSCRIPTION_TYPE_CHOICES = ()
THEDAILY_WELCOME_EMAIL_TEMPLATES = {}
THEDAILY_PROVINCE_CHOICES = []
THEDAILY_DEFAULT_CATEGORY_NEWSLETTERS = []  # category slugs for add default category newsletters in new accounts
THEDAILY_DEBUG_SIGNALS = None  # will be assigned after local settings import

# photologue
DEFAULT_BYLINE = "Difusión, S/D de autor."

# django-tagging and autocomplete-taggit
FORCE_LOWERCASE_TAGS = False
TAGGING_AUTOCOMPLETE_JS_BASE_URL = f"{STATIC_URL}jquery-tag-it/"
TAGGING_AUTOCOMPLETE_JQUERY_UI_FILE = "jquery-ui.min.js"

# home
PUBLISHING_TIME = "05:00"  # 'HH:MM'

# default logos
HOMEV3_LOGO = HOMEV3_LOGO_FOOTER = "img/logo-utopia.png"
HOMEV3_SECONDARY_LOGO = "img/logo-utopia-secondary.png"
HOMEV3_LOGO_PRINTABLE = "img/logo-utopia-printable.png"
HOMEV3_LOGO_ALT_TEXT = "utopia logo"

# default footer template
HOMEV3_FOOTER_TEMPLATE = "footer.html"

# django reCaptcha
NOCAPTCHA = True
RECAPTCHA_USE_SSL = True

# adzone
ADZONE_LOG_AD_IMPRESSIONS = True
ADZONE_LOG_AD_CLICKS = True

SHORTEN_MODELS = {
    "A": "core.article",
    "U": "short.url",
}

TINYMCE_DEFAULT_CONFIG = {
    "plugins": "table,spellchecker,paste,searchreplace",
    "theme": "advanced",
}

AUTH_USER_EMAIL_UNIQUE = True
AUTH_PROFILE_MODULE = "thedaily.Subscriber"

# TODO: use / check usage
LOGIN_URL = "/usuarios/entrar/"  # login_required decorator redirects here
LOGOUT_URL = "/usuarios/salir/"
SIGNUP_URL = "/usuarios/registro/"
LOGIN_REDIRECT_URL = "/"
LOGIN_ERROR_URL = "/usuarios/error/login/"

MESSAGETAGS = {messages.ERROR: "danger"}

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

# django-social-auth
SOCIAL_AUTH_GOOGLE_OAUTH2_STRATEGY = "social_django.strategy.DjangoStrategy"
SOCIAL_AUTH_STORAGE = "social_django.models.DjangoStorage"
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    "https://www.googleapis.com/auth/plus.me",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "libs.social_auth_pipeline.check_email_in_use",
    "social_core.pipeline.social_auth.associate_by_email",
    "social_core.pipeline.user.create_user",
    "libs.social_auth_pipeline.get_phone_number",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)
SOCIAL_AUTH_URL_NAMESPACE = "social"

# misc
COMPRESS_PRECOMPILERS = (
    ("text/less", "lessc {infile} {outfile}"),
    ("text/x-scss", "sass --scss {infile} {outfile}"),
)

BLEACH_STRIP_TAGS = True

# Online sync User fields with CRM (key=crm_contact_field_name, value=cms_subscriber_field_name)
CRM_UPDATE_SUBSCRIBER_FIELDS = {}
# Online sync User fields with CRM disabled by default
CRM_UPDATE_USER_ENABLED = False
# CRM API urls will be assigned after local_settings import, if not overrided
CRM_API_BASE_URI = None
CRM_API_UPDATE_USER_URI = None
CRM_API_GET_USER_URI = None

# PWA
PWA_SERVICE_WORKER_TEMPLATE = "core/templates/sw/serviceworker.js"
PWA_SERVICE_WORKER_VERSION = 1

# defaults that will be assigned after local settings import
COMPRESS_OFFLINE_CONTEXT = {}
SIGNUPWALL_ENABLED = None
SIGNUPWALL_HEADER_ENABLED = False
SIGNUPWALL_REMAINING_BANNER_ENABLED = True
FREEZE_TIME = None
CRM_UPDATE_USER_CREATE_CONTACT = None
CORE_ARTICLE_DETAIL_ENABLE_AMP = True
PHONENUMBER_DEFAULT_REGION = None


# ====================================================================================== visual separator =============


# Override previous settings with values in local_migration_settings.py settings file
from local_migration_settings import *  # noqa


SITE_URL_SD = f"{URL_SCHEME}://{SITE_DOMAIN}"  # "SD" stands for "Schema-Domain only", no trial slash.
SITE_URL = f"{SITE_URL_SD}/"
CSRF_TRUSTED_ORIGINS = [SITE_URL_SD]
ROBOTS_SITEMAP_URLS = [SITE_URL + "sitemap.xml"]
LOCALE_NAME = f"{LOCAL_LANG}_{LOCAL_COUNTRY}.{DEFAULT_CHARSET}"
COMPRESS_OFFLINE_CONTEXT['base_template'] = PORTAL_BASE_TEMPLATE

if locals().get("DEBUG_TOOLBAR_ENABLE"):
    # NOTE when enabled, you need to: pip install "django-debug-toolbar==4.3.0" && ./manage.py collectstatic
    INSTALLED_APPS += ('debug_toolbar',)
    MIDDLEWARE = MIDDLEWARE[:8] + ('debug_toolbar.middleware.DebugToolbarMiddleware',) + MIDDLEWARE[8:]

DEBUG = locals().get("DEBUG", False)
if DEBUG:
    MIDDLEWARE = MIDDLEWARE[:8] + ("corsheaders.middleware.CorsMiddleware",) + MIDDLEWARE[8:]

# phonenumbers default region (if not set) will default to LOCAL_COUNTRY
if PHONENUMBER_DEFAULT_REGION is None:
    PHONENUMBER_DEFAULT_REGION = LOCAL_COUNTRY

# signupwall overrided/defaults
if SIGNUPWALL_ENABLED is None:
    SIGNUPWALL_ENABLED = "signupwall.middleware.SignupwallMiddleware" in MIDDLEWARE
# header enabled only if signupwall is enabled and header itself was set to True in local_settings
SIGNUPWALL_HEADER_ENABLED = SIGNUPWALL_ENABLED and SIGNUPWALL_HEADER_ENABLED
# banner enabled if signupwall is enabled and the banner itself was not set to False in local_setings
SIGNUPWALL_REMAINING_BANNER_ENABLED = SIGNUPWALL_ENABLED and SIGNUPWALL_REMAINING_BANNER_ENABLED

# celery task queues, if not overrided, we populate with Queue objects based on default or overrided CELERY_QUEUES dict
if not CELERY_TASK_QUEUES and CELERY_QUEUES and isinstance(CELERY_QUEUES, dict):
    CELERY_TASK_QUEUES = [Queue(k, routing_key=k) for k in CELERY_QUEUES.keys()]

if FREEZE_TIME:
    freezer = freeze_time(FREEZE_TIME)
    freezer.start()

ABSOLUTE_URL_OVERRIDES = {"auth.user": SITE_URL + "usuarios/perfil/editar/"}

# AMP
CORE_ARTICLE_DETAIL_ENABLE_AMP = "amp_tools" in INSTALLED_APPS
if CORE_ARTICLE_DETAIL_ENABLE_AMP:
    MIDDLEWARE = (
        MIDDLEWARE[:-1]
        + ("amp_tools.middleware.AMPDetectionMiddleware", "core.middleware.AMP.OnlyArticleDetail")
        + (MIDDLEWARE[-1],)
    )

# CRM API
if CRM_API_BASE_URI:
    CRM_API_UPDATE_USER_URI = CRM_API_UPDATE_USER_URI or (CRM_API_BASE_URI + "updateuserweb/")
    CRM_API_GET_USER_URI = CRM_API_GET_USER_URI or (CRM_API_BASE_URI + "existsuserweb/")
if CRM_UPDATE_USER_CREATE_CONTACT is None:
    # defaults to the same value of the "base sync"
    CRM_UPDATE_USER_CREATE_CONTACT = CRM_UPDATE_USER_ENABLED

if locals().get("ENV_HTTP_BASIC_AUTH") and "API_KEY_CUSTOM_HEADER" not in locals():
    # by default, this variable is not defined, thats why we use locals() instead of set a "neutral" value
    API_KEY_CUSTOM_HEADER = "HTTP_X_API_KEY"

# thedaily default subscription type and debug signals
if "THEDAILY_SUBSCRIPTION_TYPE_DEFAULT" not in locals():
    THEDAILY_SUBSCRIPTION_TYPE_DEFAULT = \
        THEDAILY_SUBSCRIPTION_TYPE_CHOICES[0][0] if THEDAILY_SUBSCRIPTION_TYPE_CHOICES else None
if THEDAILY_DEBUG_SIGNALS is None:
    THEDAILY_DEBUG_SIGNALS = DEBUG
