"""
Django settings for core project.
Wearemania Traffic Forecasting Dashboard.
"""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


# =========================
# BASE CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# =========================
# SECURITY
# =========================

SECRET_KEY = os.getenv("SECRET_KEY")

def get_bool_env(name, default=False):
    return os.getenv(name, str(default)).lower() in ["true", "1", "yes"]


DEBUG = get_bool_env("DEBUG", False)
IS_RUNSERVER = "runserver" in sys.argv

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False if IS_RUNSERVER else get_bool_env("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = False if IS_RUNSERVER else get_bool_env("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = False if IS_RUNSERVER else get_bool_env("CSRF_COOKIE_SECURE", False)
SECURE_HSTS_SECONDS = 0 if IS_RUNSERVER else int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    False if IS_RUNSERVER else get_bool_env("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
)
SECURE_HSTS_PRELOAD = False if IS_RUNSERVER else get_bool_env("SECURE_HSTS_PRELOAD", False)


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
    db_engine = get_env_value("DB_ENGINE")

    if not db_engine:
        return build_sqlite_database_config()

    if db_engine == "django.db.backends.mysql":
        mysql_config = {
            "NAME": get_env_value("MYSQL_DATABASE"),
            "USER": get_env_value("MYSQL_USER"),
            "PASSWORD": get_env_value("MYSQL_PASSWORD"),
            "HOST": get_env_value("MYSQL_HOST"),
            "PORT": get_env_value("MYSQL_PORT", default="3306"),
        }
        missing_mysql_config = [
            name for name, value in mysql_config.items()
            if name != "PORT" and value in [None, ""]
        ]

        if missing_mysql_config:
            if IS_RUNSERVER:
                return build_sqlite_database_config()

            missing_names = ", ".join(f"DB_{name}" for name in missing_mysql_config)
            raise ImproperlyConfigured(
                f"Missing required MySQL environment variable(s): {missing_names}"
            )

        options = {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        }
        db_ssl_ca = get_env_value("DB_SSL_CA")

        if db_ssl_ca:
            options["ssl"] = {"ca": db_ssl_ca}

        return {
            "ENGINE": db_engine,
            **mysql_config,
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": options,
        }

    return {
        "ENGINE": db_engine,
        "NAME": get_env_value("MYSQL_DATABASE", default=BASE_DIR / "db.sqlite3"),
    }


def build_sqlite_database_config():
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


DATABASES = {
    "default": build_database_config(),
}

FORECAST_HISTORY_LIMIT = get_int_env("FORECAST_HISTORY_LIMIT", 10)
DEFAULT_FORECAST_DAYS = max(1, min(get_int_env("FORECAST_DAYS", 7), 14))
MAX_FORECAST_DAYS = max(1, min(get_int_env("FORECAST_MAX_DAYS", 14), 14))
FORECAST_DAYS = DEFAULT_FORECAST_DAYS


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
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
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
