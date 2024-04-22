"""
Django settings for master_mind project.

Generated by 'django-admin startproject' using Django 4.2.10.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
from corsheaders.defaults import default_headers
from infra_utils.custom_logging import LOGGING as CUSTOM_LOGGING
from dotenv import load_dotenv
from datetime import timedelta

import sentry_sdk
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


load_dotenv(override=True)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["*"]

sentry_sdk.init(
    dsn="https://15510bd5a562746a59eb19affd288394@o4507129951813632.ingest.us.sentry.io/4507129958432768",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)


# Application definition

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_q",
    "infra_utils",
    "user",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "pusher_channel_app",
    "events",
    "home",
    "dyte",
    "integrations",
    "integrations.slack",
    "integrations.google_oauth",
    "integrations.outlook",
    "integrations.caldotcom",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "master_mind.middleware.TimingMiddleware",
]

ROOT_URLCONF = "master_mind.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "master_mind.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases


DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE"),
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

Q_CLUSTER = {
    "name": "DjangORM",
    "workers": 1,
    "timeout": 90,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# theme
UNFOLD = {
    "SITE_TITLE": "Pingbase",
    "SITE_SYMBOL": "space_dashboard",
    "SITE_HEADER": "Pingbase Admin",
    "COLORS": {
        "primary": {
            "50": "240 235 255",  # Lighter lavender for a fresh, airy feel
            "100": "230 225 255",  # Soft lavender, slightly more vivid
            "200": "215 200 255",  # Clear, bright lavender
            "300": "200 175 255",  # Vivid lavender with a hint of brightness
            "400": "180 145 255",  # Rich lavender, striking yet inviting
            "500": "160 115 250",  # Deep lavender, vibrant and eye-catching
            "600": "140 90 240",  # Intense purple, for strong emphasis
            "700": "120 65 230",  # Deep purple, bold and authoritative
            "800": "100 40 220",  # Darker purple, for depth and impact
            "900": "80 15 200",  # Very deep purple, for maximum impact
            "950": "60 5 180",  # Darkest, for contrast and emphasis
        },
    },
}

LOGGING = CUSTOM_LOGGING

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
    "NON_FIELD_ERRORS_KEY": "error",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "user.authentication.SelectiveJWTAuthentication",
    ),
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=2),
}

PASSWORD_RESET_TIMEOUT = 604800  # 7 days


CSRF_TRUSTED_ORIGINS = [
    "https://api.pingbase.ai",
    "http://127.0.0.1:8000",  # Django projects running on localhost
    "http://127.0.0.1:5500",
    "wss://ws-mt1.pusher.com",
    "http://localhost:5500",
    "https://js.pusher.com",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "https://app.pingbase.ai",
    "https://*",
]

CORS_ALLOWED_ORIGINS = [
    "https://api.pingbase.ai",
    "http://127.0.0.1:8000",  # Django projects running on localhost
    "http://127.0.0.1:5500",
    "wss://ws-mt1.pusher.com",
    "http://localhost:5500",
    "https://js.pusher.com",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "https://app.pingbase.ai",
    "https://*",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://\w+\.dyte\.io$",
]

CORS_ALLOW_HEADERS = list(default_headers) + ["X-User-Token", "organization-token"]

CORS_ALLOW_ALL_ORIGINS = True  # Should find a proper way to allow public endpoints

STATIC_ROOT = BASE_DIR / "staticfiles"

SENDGRID_API_KEY = str(os.getenv("SENDGRID_API_KEY"))
EMAIL_HOST = str(os.getenv("EMAIL_HOST"))
EMAIL_HOST_USER = "apikey"
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = str(os.getenv("DEFAULT_FROM_EMAIL"))


AUTH_USER_MODEL = "user.User"

# Pusher config
PUSHER_APP_ID = os.getenv("PUSHER_APP_ID")
PUSHER_KEY = os.getenv("PUSHER_KEY")
PUSHER_SECRET = os.getenv("PUSHER_SECRET")
PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER")

# Dyte config
DYTE_ORG_ID = os.getenv("DYTE_ORG_ID")
DYTE_API_KEY = os.getenv("DYTE_API_KEY")
DYTE_BASE_URL = os.getenv("DYTE_BASE_URL")
DYTE_AZURE_BLOB_URL = os.getenv("DYTE_AZURE_BLOB_URL")
DYTE_WEBHOOK_ID = os.getenv("DYTE_WEBHOOK_ID")

# Azure
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_PINGBASE_APP_CLIENT_ID = os.getenv("AZURE_PINGBASE_APP_CLIENT_ID")
AZURE_PINGBASE_APP_TENANT_ID = os.getenv("AZURE_PINGBASE_APP_TENANT_ID")
AZURE_PINGBASE_APP_CLIENT_SECRET_ID = os.getenv("AZURE_PINGBASE_APP_CLIENT_SECRET_ID")
AZURE_PINGBASE_APP_CLIENT_SECRET_VALUE = os.getenv(
    "AZURE_PINGBASE_APP_CLIENT_SECRET_VALUE"
)


# UPLEAD
UPLEAD_API_KEY = os.getenv("UPLEAD_API_KEY")
UPLEAD_BASE_URL = os.getenv("UPLEAD_BASE_URL")

# SLACK
SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")


# CALDOTCOM
CAL_DOT_COM_CLIENT_ID = os.getenv("CAL_DOT_COM_CLIENT_ID")
CAL_DOT_COM_CLIENT_SECRET = os.getenv("CAL_DOT_COM_CLIENT_SECRET")


# REVERSE CONTACT
REVERSE_CONTACT_API_KEY = os.getenv("REVERSE_CONTACT_API_KEY")
REVERSE_CONTACT_BASE_URL = os.getenv("REVERSE_CONTACT_BASE_URL")
