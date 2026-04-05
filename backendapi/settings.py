"""
Django settings for backendapi project.
"""

from pathlib import Path
import os
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _csv_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default) or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production-environment')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(os.getenv('DEBUG', 0))

ALLOWED_HOSTS = _csv_env("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = _csv_env("CORS_ORIGINS")

# CORS: allow-all only in DEBUG (local). Production/staging must list origins (e.g. Vercel).
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    if not CORS_ALLOWED_ORIGINS:
        raise ImproperlyConfigured(
            "Set CORS_ORIGINS to a comma-separated list of frontend origins (e.g. your Vercel URLs). "
            "CORS_ALLOW_ALL_ORIGINS is disabled when DEBUG=0."
        )

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',  # Django REST framework
    'rest_framework_simplejwt',  # JWT authentication
    'drf_spectacular',  # Swagger/OpenAPI documentation
    'corsheaders',
    'multiselectfield',
    "phonenumber_field",

    # Apps
    'dashboard',
    'ResumeReviewDay',
    'career_fair',
]

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Tribunal API',
    'DESCRIPTION': 'API for managing tribunal dashboard',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
    },
}

# JWT settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backendapi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backendapi.wsgi.application'


def _merge_pg_options(options: dict, host: str = "") -> dict:
    """
    For non-pooler Postgres, set search_path=public when needed after odd restores.

    Neon's *pooled* endpoint rejects startup option search_path — use a direct host
    for migrate or omit this on -pooler hosts.
    https://neon.tech/docs/connect/connection-errors#unsupported-startup-parameter
    """
    out = dict(options)
    host_l = (host or "").lower()
    is_neon_pooler = "-pooler" in host_l
    if is_neon_pooler:
        return out
    existing = (out.get("options") or "").strip()
    if "search_path" not in existing:
        suffix = "-c search_path=public,pg_catalog"
        out["options"] = f"{existing} {suffix}".strip() if existing else suffix
    return out


def _database_from_url(url: str) -> dict:
    """Parse a PostgreSQL URI (e.g. Neon) into Django DATABASES['default']."""
    tmp = urlparse(url)
    name = (tmp.path or "").lstrip("/") or "postgres"
    host = tmp.hostname or ""
    options = _merge_pg_options(
        dict(parse_qsl(tmp.query, keep_blank_values=True)),
        host=host,
    )
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": unquote(tmp.username) if tmp.username else "",
        "PASSWORD": unquote(tmp.password) if tmp.password else "",
        "HOST": host,
        "PORT": tmp.port or 5432,
        "OPTIONS": options,
    }


# Database — prefer DATABASE_URL (Neon console "connection string") for Render/staging.
# Falls back to split env vars (DB_USERNAME, DB_PASSWORD, DB_URL=host, DB_HOST=port).
_database_url = (os.getenv("DATABASE_URL") or "").strip()
if _database_url:
    DATABASES = {"default": _database_from_url(_database_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "postgres"),
            "USER": os.getenv("DB_USERNAME"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_URL"),
            "PORT": os.getenv("DB_HOST"),
            "OPTIONS": _merge_pg_options({}, host=os.getenv("DB_URL", "") or ""),
        },
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'dashboard.validators.TribunalPasswordValidator',
    },
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': int(os.getenv('REST_FRAMEWORK_PAGE_SIZE', 10)),
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Swagger settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
}

# Internationalization
LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'en-us')
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/' if not DEBUG else 'static/'
STATIC_ROOT = BASE_DIR / 'static'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = 'media/'

if not DEBUG:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

# Trusted origins for CSRF (admin POST, etc.) — include https://<your-service>.onrender.com on Render.
CSRF_TRUSTED_ORIGINS = _csv_env("CSRF_TRUSTED_ORIGINS")

# Security settings
if not DEBUG:
    SECURE_SSL_REDIRECT = bool(int(os.getenv('SECURE_SSL_REDIRECT', 0)))
    SESSION_COOKIE_SECURE = bool(int(os.getenv('SESSION_COOKIE_SECURE', 1)))
    CSRF_COOKIE_SECURE = bool(int(os.getenv('CSRF_COOKIE_SECURE', 1)))
    # Render terminates TLS; forward proto so request.is_secure() and secure cookies behave.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
