import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
ROOT_URLCONF = 'standalone_django_project.urls'
WSGI_APPLICATION = 'standalone_django_project.wsgi.application'
SITE_ID = 1

SITE_NAME = os.environ.get("SITE_NAME")
SITE_DOMAIN = os.environ['SITE_DOMAIN']
HEROKU_DOMAIN = os.environ.get('HEROKU_DOMAIN')

import actionkit_usersearch
GEONAMES_API_USERNAME = actionkit_usersearch.SETTINGS['GEONAMES_API_USERNAME']

ALLOWED_HOSTS = [SITE_DOMAIN]
if HEROKU_DOMAIN:
    ALLOWED_HOSTS.append(HEROKU_DOMAIN)

if os.environ.get('DJANGO_DEBUG'):
    DEBUG = True
else:
    DEBUG = False
TEMPLATE_DEBUG = DEBUG

ACTIONKIT_DATABASE_NAME = os.environ['ACTIONKIT_DATABASE_NAME']
ACTIONKIT_DATABASE_USER = os.environ['ACTIONKIT_DATABASE_USER']
ACTIONKIT_DATABASE_PASSWORD = os.environ['ACTIONKIT_DATABASE_PASSWORD']

import dj_database_url
DATABASES = {
    'default': dj_database_url.config(),
    'ak': {
        'ENGINE': "django.db.backends.mysql",
        'NAME': ACTIONKIT_DATABASE_NAME,
        'USER': ACTIONKIT_DATABASE_USER,
        'PASSWORD': ACTIONKIT_DATABASE_PASSWORD,
        'HOST': "client-db.actionkit.com",
        'PORT': "",
        }
    }
DATABASES['dummy'] = actionkit_usersearch.DATABASES['dummy']

SECRET_KEY = os.environ["DJANGO_SECRET"]

ACTIONKIT_API_HOST = os.environ['ACTIONKIT_API_HOST']
ACTIONKIT_API_USER = os.environ['ACTIONKIT_API_USER']
ACTIONKIT_API_PASSWORD = os.environ['ACTIONKIT_API_PASSWORD']

TEMPLATE_LOADERS = (
    'dbtemplates.loader.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'gunicorn',
    'south',
    'django.contrib.flatpages',

    'dbtemplates',
    'djangohelpers',

    'standalone_django_project',  # For the template finder

    'actionkit',

    'actionkit_usersearch',
    'actionkit_userdetail',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.request",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "standalone_django_project.context_processors.globals",
)

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    ]

OAUTH_REDIRECT_URI_ENFORCE_PREFIX_ONLY = True

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.transaction.TransactionMiddleware',

    "djangohelpers.middleware.AuthRequirementMiddleware",
)
ANONYMOUS_PATHS = (
    "/static/",
    "/admin/",
    "/accounts/",
    )

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'

if os.environ.get('DJANGO_DEBUG_TOOLBAR'):
    MIDDLEWARE_CLASSES += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
        )
    INSTALLED_APPS += (
        'debug_toolbar',
        )
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        }
    INTERNAL_IPS = os.environ.get("INTERNAL_IPS")
    if INTERNAL_IPS is None:
        INTERNAL_IPS = []
    elif INTERNAL_IPS.strip() in ("*", "0.0.0.0"):
        class AllIPS(list):
            def __contains__(self, item):
                return True
        INTERNAL_IPS = AllIPS()
    else:
        INTERNAL_IPS = [i.strip() for i in INTERNAL_IPS.split()]

STATIC_URL = "/static/"
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'collected_static')

