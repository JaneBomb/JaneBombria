import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# DEBUG = "TRUE"
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

# SECRET_KEY
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        from django.core.management.utils import get_random_secret_key

        SECRET_KEY = get_random_secret_key()
    else:
        raise RuntimeError("DJANGO_SECRET_KEY environment variable must be set when DEBUG=False.")


ALLOWED_HOSTS = [
    "bearestate.me",
    "www.bearestate.me",
    "premain.bearestate.me",
    "127.0.0.1",
    "localhost",
]

CSRF_TRUSTED_ORIGINS = [
    "https://bearestate.me",
    "https://www.bearestate.me",
    "https://premain.bearestate.me",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# X-Content-Type-Options: nosniff
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
# clickjacking defense
X_FRAME_OPTIONS = "DENY"


# Cookie hardening that's safe to leave on everywhere:
# Django default
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"


# Production-only HTTPS hardening. We only flip these on when DEBUG is False so local dev over plain HTTP keeps working.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    # 1 year HSTS, including subdomains + preload eligibility.
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# API KEYS
RENTCAST_API_KEY = os.environ.get("RENTCAST_API_KEY")
OPENAI_MODEL5_API_KEY = os.environ.get("OPENAI_MODEL5_API_KEY")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "home",
    "behave_django",
    "channels",
    "chat",
    "socialPosts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR.parent / "templates"],
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

WSGI_APPLICATION = "myproject.wsgi.application"


# Database

# Path name for the database that imports the databse path
# from a set enviornment variable named "DATABASE_PATH",
# and falls back to the default database if the
# file cannot be found
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "db.sqlite3"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Set the database pathway to be what path DATABASE_PATH collected from the decleration above
        "NAME": DATABASE_PATH,
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "home" / "static",
]

# Media Files
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT_PATH", str(BASE_DIR / "media")))

# Login redirects

LOGIN_URL = "/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Use the Django Channels features
ASGI_APPLICATION = "myproject.asgi.application"

# In development, codes print to the terminal instead of being sent.
# In production, swap EMAIL_BACKEND and fill in the SMTP settings below.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")  # dev default
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
# Redis channel layer
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

# Cache backend used by the rate limiter (home/security.py).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "bearestate-default",
    }
}

# The test flips this on
RATE_LIMIT_DISABLED = False

# When tests are run, adjust ASGI Server
TESTING = False
