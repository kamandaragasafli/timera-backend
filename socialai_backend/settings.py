"""
Django settings for socialai_backend project.

AI Social Media Management Tool Backend
"""

from pathlib import Path
from decouple import config as decouple_config, Config, RepositoryEnv
from datetime import timedelta
import os
import sys
import logging

# -------------------------
# ENV LOADING (local.env)
# -------------------------
env_file = Path(__file__).resolve().parent.parent / "local.env"
if env_file.exists():
    config = Config(RepositoryEnv(str(env_file)))
else:
    config = decouple_config  # fall back to system env

# -------------------------
# BASE
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------
# SECURITY (PRODUCTION-SAFE)
# -------------------------
# ✅ No default in code. Must be provided via env/local.env
SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", default=False, cast=bool)

# Comma-separated env, e.g.: "timera.az,www.timera.az,timera-backend.trivasoft.az"
ALLOWED_HOSTS = [
    h.strip()
    for h in config("ALLOWED_HOSTS", default="timera-backend.trivasoft.az,www.timera.az,localhost,127.0.0.1").split(",")
    if h.strip()
]

# -------------------------
# APPLICATION DEFINITION
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",

    # Local apps
    "accounts",
    "posts",
    "social_accounts",
    "ai_helper",
    "meta_ads",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "socialai_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "socialai_backend.wsgi.application"

# -------------------------
# DATABASE
# -------------------------
# NOTE: SQLite is OK for dev; production should use PostgreSQL.
# You can switch by setting DB_ENGINE=postgres and providing DB_* envs.
DB_ENGINE = config("DB_ENGINE", default="sqlite")

if DB_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -------------------------
# PASSWORD VALIDATION
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------
# INTERNATIONALIZATION
# -------------------------
LANGUAGE_CODE = "az"  # Azerbaijani
TIME_ZONE = "Asia/Baku"  # Baku time (UTC+4)
USE_I18N = True
USE_TZ = True

# -------------------------
# STATIC / MEDIA
# -------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------
# AUTH
# -------------------------
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailBackend"]

# -------------------------
# DRF (WITH THROTTLING)
# -------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,

    # ✅ Throttling (defense-in-depth)
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("THROTTLE_ANON", default="30/min"),
        "user": config("THROTTLE_USER", default="120/min"),
    },

    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

# -------------------------
# JWT
# -------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

# -------------------------
# CORS / CSRF
# -------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://timera.az",
    "https://www.timera.az",
]
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_EXPOSE_HEADERS = ["content-type", "x-csrftoken"]

# ✅ Needed when using cookies/session across origins
CSRF_TRUSTED_ORIGINS = [
    "https://timera.az",
    "https://www.timera.az",
]

# -------------------------
# UPLOAD LIMITS
# -------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# -------------------------
# CELERY
# -------------------------
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# -------------------------
# EXTERNAL API KEYS
# -------------------------
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
APIFY_API_KEY = config("APIFY_API_KEY", default="")
WASK_API_URL = config("WASK_API_URL", default="https://api.wask.co/v1/generate-logo-slogan")
WASK_API_KEY = config("WASK_API_KEY", default="")
IDEOGRAM_API_KEY = config("IDEOGRAM_API_KEY", default="")
FAL_AI_API_KEY = config("FAL_AI_API_KEY", default="")

PEXELS_API_KEY = config("PEXELS_API_KEY", default="")
PIXABAY_API_KEY = config("PIXABAY_API_KEY", default="")
UNSPLASH_API_KEY = config("UNSPLASH_API_KEY", default="")

SUPABASE_URL = config("SUPABASE_URL", default="")
SUPABASE_SERVICE_ROLE_KEY = config("SUPABASE_SERVICE_ROLE_KEY", default="")
SUPABASE_BUCKET = config("SUPABASE_BUCKET", default="timera-media")

PLACID_API_KEY = config("PLACID_API_KEY", default="")
PLACID_DEFAULT_TEMPLATE = config("PLACID_DEFAULT_TEMPLATE", default="")

CANVA_API_KEY = config("CANVA_API_KEY", default="")
CANVA_CLIENT_ID = config("CANVA_CLIENT_ID", default="")
CANVA_CLIENT_SECRET = config("CANVA_CLIENT_SECRET", default="")

LINKEDIN_CLIENT_ID = config("LINKEDIN_CLIENT_ID", default="")
LINKEDIN_CLIENT_SECRET = config("LINKEDIN_CLIENT_SECRET", default="")
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")

N8N_WEBHOOK_URL = config("N8N_WEBHOOK_URL", default="")
N8N_API_KEY = config("N8N_API_KEY", default="")

# -------------------------
# LOGGING (AUTO-CREATE logs/)
# -------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

class UTF8StreamHandler(logging.StreamHandler):
    """StreamHandler with UTF-8 encoding support for Windows"""
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if hasattr(stream, "buffer"):
                stream.buffer.write(msg.encode("utf-8", errors="replace"))
                stream.buffer.write(self.terminator.encode("utf-8"))
            else:
                stream.write(msg)
                stream.write(self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{levelname}] {asctime} {module} {message}", "style": "{"},
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "django.log"),
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "console": {
            "level": "DEBUG",
            "()": UTF8StreamHandler,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console", "file"], "level": "WARNING", "propagate": False},
        "posts": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "accounts": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
    },
}

# -------------------------
# META OAUTH
# -------------------------
META_APP_ID = config("META_APP_ID", default="")
META_APP_SECRET = config("META_APP_SECRET", default="")
META_WEBHOOK_VERIFY_TOKEN = config("META_WEBHOOK_VERIFY_TOKEN", default="timera_webhook_token")

BACKEND_URL = config("BACKEND_URL", default="http://localhost:8000")
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")

# -------------------------
# SESSION / CSRF COOKIES
# -------------------------
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True

# -------------------------
# PRODUCTION SECURITY HEADERS
# -------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(config("SECURE_HSTS_SECONDS", default="2592000"))  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    REFERRER_POLICY = "same-origin"

    # If behind nginx/cloudflare:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -------------------------
# SPECTACULAR (unchanged)
# -------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Timera API Documentation",
    "DESCRIPTION": "AI Social Media Management Tool API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "AUTHENTICATION_WHITELIST": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
    "REDOC_UI_SETTINGS": {
        "hideDownloadButton": False,
        "hideHostname": False,
        "hideSingleRequestSample": False,
    },
}
