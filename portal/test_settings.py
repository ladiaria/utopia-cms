# import faulthandler

from settings import *


# This can be useful to debug segmentation fault errors
# faulthandler.enable()

INSTALLED_APPS = (
    'django_mobile',
    'django.contrib.staticfiles',
    'admin_shortcuts',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.comments',
    'django.contrib.contenttypes',
    'django.contrib.markup',
    'django.contrib.sessions',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.formtools',
    'django.contrib.webdesign',
    'background_task',
    'subdomains',
    'sitemaps',
    'south',
    'django_nose',
    'audiologue',
    'tagging',
    'core',
    'core.attachments',
    'django_extensions',
    'generator',
    'memcached',
    'shoutbox',
    'thedaily',
    'videologue',
    'short',
    'adzone',
    'exchange',
    'faq',
    'captcha',
    'photologue',
    'photologue_ladiaria',
    'robots',
    'search',
    'sorl.thumbnail',
    'shorturls',
    'less',
    'django_user_agents',
    'updown',
    'materialize',
    'crispy_forms',
    'crispy_forms_materialize',
    'actstream',
    'django.contrib.messages',
    'signupwall',
    'homev3',
    'cartelera',
    'markdown',
    'django_markdown',
    'comunidad',
    'appconf',
    'djangoratings',
    'tagging_autocomplete_tagit',
    'avatar',
    'endless_pagination',
    'notification',
    'django.contrib.flatpages',
    'epubparser',
    'dashboard',
    'django_filters',
    'rest_framework',
    'compressor',
    'favit',
)

if DEBUG:
    # remove debug_toolbar middleware (if present)
    if 'debug_toolbar.middleware.DebugToolbarMiddleware' in MIDDLEWARE_CLASSES:
        m_list = list(MIDDLEWARE_CLASSES)
        m_list.remove('debug_toolbar.middleware.DebugToolbarMiddleware')
        MIDDLEWARE_CLASSES = tuple(m_list)
