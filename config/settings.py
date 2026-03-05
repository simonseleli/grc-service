from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS: List[str] = [
    "localhost",
    "localhost:8080",
    "127.0.0.1",
    "0.0.0.0",
    "grc-service",
    "iam-service",  # Nginx proxy sometimes sends this as Host header
    os.getenv("TUNNEL_DOMAIN", "fcc.tunnel.ictpack.net"),
    os.getenv("EXTERNAL_DOMAIN", "fcc.tunnel.ictpack.net"),
]
ALLOWED_HOSTS.extend([host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()])
ALLOWED_HOSTS = sorted({host for host in ALLOWED_HOSTS if host})

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",  # FIMS standard - required for DjangoFilterBackend
    "apps.api",
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.permission_middleware.JWTPermissionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "fims_grc"),
        "USER": os.getenv("DB_USER", "grc_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "grc_password_2024"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.api.authentication.IAMJWTAuthentication",
        "apps.api.authentication.ServiceAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Pagination settings (FIMS standard - matches Document Records, IAM)
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "PAGE_SIZE_QUERY_PARAM": "page_size",
    "MAX_PAGE_SIZE": 100,
    # Filter backends (FIMS standard - matches Document Records, IAM)
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    # Renderer (JSON only - matches Document Records, IAM)
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    # Exception handler (FIMS standard - consistent error format)
    "EXCEPTION_HANDLER": "apps.api.exceptions.custom_exception_handler",
}

# JWT Configuration (shared with IAM service)
# CRITICAL: Must be defined BEFORE SIMPLE_JWT so it can reference this variable
# CRITICAL: Must use the SAME secret as IAM service for token validation
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY environment variable is required and must match IAM service. "
        "This ensures all services can validate tokens issued by IAM."
    )
JWT_ALGORITHM = "HS256"

# Django REST Framework SimpleJWT settings (FIMS Integration)
from datetime import timedelta

SIMPLE_JWT = {
    'SIGNING_KEY': JWT_SECRET_KEY,  # Use validated JWT_SECRET_KEY (no fallback!)
    'ALGORITHM': JWT_ALGORITHM,
    'VERIFY_SIGNATURE': True,
    'VERIFYING_KEY': None,  # For symmetric algorithms (HS256), this is not needed
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

SPECTACULAR_SETTINGS = {
    "TITLE": "GRC Service API",
    "VERSION": "0.1.0",
    "DESCRIPTION": "Governance, Risk, and Compliance service for FCC",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

SERVICE_NAME = "grc-service"

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_CONFIG = {
    "client_id": os.getenv("KAFKA_CLIENT_ID", SERVICE_NAME),
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/1"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/2"))
CELERY_TASK_ALWAYS_EAGER = False

# Celery Beat schedule — periodic tasks
from celery.schedules import crontab  # noqa: E402
CELERY_BEAT_SCHEDULE = {
    'check-monitoring-deadlines-daily': {
        'task': 'grc.check_monitoring_deadlines',
        'schedule': crontab(hour=7, minute=0),  # Every day at 07:00
        'options': {'queue': 'default'},
    },
}

# JWT token lifetime settings
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "60"))
JWT_REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))

# Service URLs (FIMS Integration)
IAM_SERVICE_URL = os.getenv("IAM_SERVICE_URL", "http://iam-service:8000")
DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL", "http://document-records-service:8002")
WORK_ORCHESTRATION_SERVICE_URL = os.getenv("WORK_ORCHESTRATION_SERVICE_URL", "http://work-orchestration-service:8004")

# Workflow Template UUIDs — resolved automatically by OrchestrationClient._get_template_id_by_code()
# at runtime from WO's template list API (guide §4.3 pattern). No need to set these manually.
# To seed GRC templates into WO, run inside the WO container:
#   python manage.py seed_workflow_templates
# To verify resolved UUIDs, run inside the GRC container:
#   python manage.py register_workflow_templates --fetch

# Service-to-service authentication token (FIMS standard name)
SERVICE_TO_SERVICE_TOKEN = os.getenv("SERVICE_TO_SERVICE_TOKEN", "fims-service-secret-token")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO" if not DEBUG else "DEBUG",
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
