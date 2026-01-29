import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit, urljoin

# -------------------------
# Helpers
# -------------------------
def _env_str(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return default if v is None else str(v)

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}

def _split_env_csv(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x and x.strip()]

def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

def _normalize_origin(origin: str, *, allow_wildcard: bool = False) -> str | None:
    if not origin:
        return None

    o = origin.strip().rstrip("/")

    if allow_wildcard and "*" in o:
        if o.startswith("http://") or o.startswith("https://"):
            return o
        return None

    try:
        parts = urlsplit(o)
    except Exception:
        return None

    if parts.scheme not in ("http", "https"):
        return None
    if not parts.netloc:
        return None
    if parts.path or parts.query or parts.fragment:
        return None

    return f"{parts.scheme}://{parts.netloc}"

def get_cors_allowed_origins(*, debug: bool) -> list[str]:
    origins: list[str] = []
    frontend = os.environ.get("FRONTEND_URL")
    if frontend:
        origins.append(frontend)

    origins.extend(_split_env_csv("EXTRA_CORS_ALLOWED_ORIGINS"))

    if debug or _env_bool("ALLOW_DEV_CORS_ORIGINS", False):
        origins.extend(_split_env_csv("DEV_CORS_ALLOWED_ORIGINS") or [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ])

    normalized = [_normalize_origin(o) for o in origins]
    return _dedupe([x for x in normalized if x])

def get_csrf_trusted_origins(*, debug: bool) -> list[str]:
    origins: list[str] = []
    frontend = os.environ.get("FRONTEND_URL")
    if frontend:
        origins.append(frontend)

    origins.extend(_split_env_csv("EXTRA_CSRF_TRUSTED_ORIGINS"))

    if debug or _env_bool("ALLOW_DEV_CSRF_TRUSTED_ORIGINS", False):
        origins.extend(_split_env_csv("DEV_CSRF_TRUSTED_ORIGINS") or [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ])

    normalized = [_normalize_origin(o, allow_wildcard=True) for o in origins]
    return _dedupe([x for x in normalized if x])

def get_ws_allowed_origins(*, debug: bool) -> list[str]:
    origins: list[str] = []
    frontend = os.environ.get("FRONTEND_URL")
    if frontend:
        origins.append(frontend)

    origins.extend(_split_env_csv("EXTRA_WS_ALLOWED_ORIGINS"))

    if debug or _env_bool("ALLOW_DEV_WS_ORIGINS", False):
        origins.extend(_split_env_csv("DEV_WS_ALLOWED_ORIGINS") or [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ])

    normalized = [_normalize_origin(o) for o in origins]
    return _dedupe([x for x in normalized if x])


PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")  # e.g. https://api.example.com
DEEFAKE_UPLOAD_MAX_BYTES = int(os.environ.get("DEEFAKE_UPLOAD_MAX_BYTES", str(500 * 1024 * 1024)))  # 500MB default

DEEFAKE_ALLOWED_EXTS = {
    "wav", "mp3", "m4a", "mp4", "webm", "mov",
    "png", "jpg", "jpeg"  # if you allow image/video too
}

DEEFAKE_ALLOWED_MIME_PREFIXES = (
    "audio/",
    "video/",
    "image/",
)

def build_public_media_url(path_under_media: str) -> str:
    """
    path_under_media: e.g. "deepfake/20260128/<uuid>.wav"
    """
    base = PUBLIC_BASE_URL
    if not base:
        # fallback: request.build_absolute_uri should be used in views
        return ""

    # MEDIA_URL is like "/static/media/"
    return urljoin(base.rstrip("/") + "/", (MEDIA_URL.lstrip("/") + path_under_media).replace("//", "/"))



# -------------------------
# Base
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY is not set in environment.")

DEBUG = _env_bool("DEBUG", False)

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]


# -------------------------
# Apps
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",

    "corsheaders",
    "csp",

    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    "channels",
    "core",
    "user",
    "tts",
    "stt",
    "voices",
    "deepfake",
]

ASGI_APPLICATION = "app.asgi.application"


# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "csp.middleware.CSPMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# -------------------------
# URLs / Templates
# -------------------------
ROOT_URLCONF = "app.urls"

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

# WSGI not used by Daphne, but harmless to keep for tooling
WSGI_APPLICATION = "app.wsgi.application"


# -------------------------
# Database (supports POSTGRES_* and DB_*)
# -------------------------
DB_HOST = os.environ.get("DB_HOST") or os.environ.get("POSTGRES_HOST", "db-stc")
DB_PORT = os.environ.get("DB_PORT") or os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME") or os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("DB_USER") or os.environ.get("POSTGRES_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
    }
}


# -------------------------
# Internationalization
# -------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# -------------------------
# Static / Media
# -------------------------
STATIC_URL = "/static/static/"
MEDIA_URL = "/static/media/"
MEDIA_ROOT = "/vol/web/media"
STATIC_ROOT = "/vol/web/static"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = 'core.User'

# -------------------------
# DRF + JWT
# -------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",

    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.auth.cookie_jwt.CookieJWTAuthentication",
    ],

    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "5000/hour",
        "login": "5/minute",
    },
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "STC Voice Platform API",
    "DESCRIPTION": "Backend APIs for Resemble-powered voice generation.",
    "VERSION": "0.1.0",
    "SECURITY": [{"cookieJWT": []}],
    "COMPONENT_SPLIT_REQUEST": True,
}



# -------------------------
# CORS / CSRF / Cookies
# -------------------------
CORS_ALLOWED_ORIGINS = get_cors_allowed_origins(debug=DEBUG)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = get_csrf_trusted_origins(debug=DEBUG)

WS_ALLOWED_ORIGINS = get_ws_allowed_origins(debug=DEBUG)
WS_ALLOW_AUTH_HEADER = _env_bool("WS_ALLOW_AUTH_HEADER", False)

JWT_ACCESS_COOKIE_NAME  = _env_str("JWT_ACCESS_COOKIE_NAME", "access_token") or "access_token"
JWT_REFRESH_COOKIE_NAME = _env_str("JWT_REFRESH_COOKIE_NAME", "refresh_token") or "refresh_token"

JWT_COOKIE_SAMESITE = _env_str("JWT_COOKIE_SAMESITE", "None") or "None"   # None/Lax/Strict
JWT_COOKIE_SECURE   = _env_bool("JWT_COOKIE_SECURE", default=(not DEBUG))
JWT_COOKIE_DOMAIN   = os.environ.get("JWT_COOKIE_DOMAIN")

JWT_ACCESS_COOKIE_PATH  = _env_str("JWT_ACCESS_COOKIE_PATH", "/") or "/"
JWT_REFRESH_COOKIE_PATH = _env_str("JWT_REFRESH_COOKIE_PATH", "/api/auth/") or "/api/auth/"

CSRF_COOKIE_SECURE   = JWT_COOKIE_SECURE
CSRF_COOKIE_SAMESITE = JWT_COOKIE_SAMESITE
CSRF_COOKIE_DOMAIN   = os.environ.get("CSRF_COOKIE_DOMAIN")

SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", default=(not DEBUG))
SESSION_COOKIE_DOMAIN = os.environ.get("SESSION_COOKIE_DOMAIN")


# -------------------------
# Channels / Redis
# -------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis-stc:6379/0")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}


# -------------------------
# Celery
# -------------------------
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"


# -------------------------
# Basic security headers
# -------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", default=(not DEBUG))


# -------------------------
# CSP (minimal safe baseline)
# -------------------------
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ("'self'",),
        "script-src": ("'self'", "https://cdn.jsdelivr.net", "'unsafe-inline'"),
        "style-src": (
            "'self'",
            "https://cdn.jsdelivr.net",
            "'sha256-MMpT0iDxyjALd9PdfepImGX3DBfJPXZ4IlDWdPAgtn0='",
        ),
        "img-src": ("'self'", "data:", "https://cdn.jsdelivr.net"),
        "font-src": ("'self'", "https://cdn.jsdelivr.net"),
        "connect-src": ("'self'", "https://cdn.jsdelivr.net"),
    }
}



# -------------------------
# Resemble config
# -------------------------
RESEMBLE_API_KEY = os.environ.get("RESEMBLE_API_KEY")
RESEMBLE_PROJECT_UUID = os.environ.get("RESEMBLE_PROJECT_UUID")
RESEMBLE_VOICE_UUID = os.environ.get("RESEMBLE_VOICE_UUID")
