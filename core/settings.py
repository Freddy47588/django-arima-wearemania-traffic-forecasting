"""
Django settings for core project.
Wearemania Traffic Forecasting Dashboard.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# =========================
# BASE CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# =========================
# SECURITY
# =========================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-wearemania-local-development-key"
)

DEBUG = os.getenv("DEBUG", "True").lower() in ["true", "1", "yes"]

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]


# =========================
# APPLICATIONS
# =========================

INSTALLED_APPS = [
    # Django default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "analytics",
]


# =========================
# MIDDLEWARE
# =========================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================
# URL / WSGI
# =========================

ROOT_URLCONF = "core.urls"

WSGI_APPLICATION = "core.wsgi.application"


# =========================
# TEMPLATES
# =========================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# =========================
# DATABASE
# =========================

def get_env_value(*names, default=None):
    for name in names:
        value = os.getenv(name)

        if value not in [None, ""]:
            return value

    return default


def get_int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def build_database_config():
    mysql_env_present = bool(
        get_env_value("DB_HOST", "MYSQL_HOST") or
        get_env_value("DB_NAME", "MYSQL_DATABASE")
    )
    db_engine = get_env_value(
        "DB_ENGINE",
        default=(
            "django.db.backends.mysql"
            if mysql_env_present else
            "django.db.backends.sqlite3"
        ),
    )

    if db_engine == "django.db.backends.mysql":
        options = {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        }
        db_ssl_ca = get_env_value("DB_SSL_CA", "MYSQL_SSL_CA")

        if db_ssl_ca:
            options["ssl"] = {"ca": db_ssl_ca}

        return {
            "ENGINE": db_engine,
            "NAME": get_env_value("DB_NAME", "MYSQL_DATABASE"),
            "USER": get_env_value("DB_USER", "MYSQL_USER"),
            "PASSWORD": get_env_value("DB_PASSWORD", "MYSQL_PASSWORD"),
            "HOST": get_env_value("DB_HOST", "MYSQL_HOST"),
            "PORT": get_env_value("DB_PORT", "MYSQL_PORT", default="3306"),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": options,
        }

    return {
        "ENGINE": db_engine,
        "NAME": get_env_value("DB_NAME", default=BASE_DIR / "db.sqlite3"),
    }


DATABASES = {
    "default": build_database_config(),
}

FORECAST_HISTORY_LIMIT = get_int_env("FORECAST_HISTORY_LIMIT", 10)
FORECAST_DAYS = get_int_env("FORECAST_DAYS", 7)


# =========================
# PASSWORD VALIDATION
# =========================

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


# =========================
# INTERNATIONALIZATION
# =========================

LANGUAGE_CODE = "id-id"

TIME_ZONE = "Asia/Jakarta"

USE_I18N = True

USE_TZ = True


# =========================
# STATIC FILES
# =========================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
] if (BASE_DIR / "static").exists() else []

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_USE_FINDERS = os.getenv(
    "WHITENOISE_USE_FINDERS",
    "True",
).lower() in ["true", "1", "yes"]


# =========================
# MEDIA FILES
# =========================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# =========================
# DEFAULT PRIMARY KEY
# =========================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================
# AUTH REDIRECT SETTINGS
# =========================

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "dashboard"

LOGOUT_REDIRECT_URL = "login"
