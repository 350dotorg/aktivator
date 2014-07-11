INSTALLED_APPS = [
    'actionkit_usersearch',
    ]

URLCONFS = [
    ("^user/search/", "actionkit_usersearch.urls"),
    ]

import dj_database_url
import os

ACTIONKIT_DUMMY_DATABASE_URL = os.environ.get(
    'ACTIONKIT_DUMMY_DATABASE_URL') or "CLEARDB_DATABASE_URL"

DATABASES = {
    'dummy': dj_database_url.parse(os.environ[ACTIONKIT_DUMMY_DATABASE_URL])
    }

SETTINGS = {
    'GEONAMES_API_USERNAME': os.environ.get('GEONAMES_API_USERNAME', "demo"),
    }

