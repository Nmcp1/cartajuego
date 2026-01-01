from pathlib import Path
from datetime import timedelta
import os
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"

# En prod, mejor setearlo en Render. Dejo fallback por si acaso.
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",

    # Local apps
    "accounts",
    "game",
    "webui",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# =========================
# DATABASE: SOLO Neon (Postgres)
# =========================
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definido. Este proyecto usa SOLO Neon/Postgres.")

u = urlparse(DATABASE_URL)
db_name = u.path.lstrip("/") if u.path else ""
qs = parse_qs(u.query or "")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db_name,
        "USER": u.username or "",
        "PASSWORD": u.password or "",
        "HOST": u.hostname or "",
        "PORT": u.port or 5432,
        "OPTIONS": {
            # Neon a veces exige SSL
            "sslmode": qs.get("sslmode", ["require"])[0],
        },
    }
}

# =========================
# AUTH / PASSWORDS
# =========================
AUTH_PASSWORD_VALIDATORS = [
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# =========================
# STATICFILES (FIX collectstatic)
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Si tienes una carpeta /static en tu repo (por ejemplo static/css, static/img), inclúyela.
STATICFILES_DIRS = []
if (BASE_DIR / "static").exists():
    STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================
# REST FRAMEWORK / JWT
# =========================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# =========================
# CORS
# =========================
CORS_ALLOW_ALL_ORIGINS = True

# =========================
# CHANNELS
# =========================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# =========================
# MEDIA (uploads del admin)
# =========================
MEDIA_URL = "/media/"

# En Render, los archivos subidos (MEDIA) deben vivir en un storage persistente,
# o se perderán en redeploy. Si tienes un Render Disk, normalmente se monta en /var/data.
RENDER_DISK_PATH = os.getenv("RENDER_DISK_PATH", "/var/data")
if os.path.isdir(RENDER_DISK_PATH):
    MEDIA_ROOT = Path(RENDER_DISK_PATH) / "media"
else:
    MEDIA_ROOT = BASE_DIR / "media"

# Asegura que exista el directorio en runtime (no falla si ya existe).
os.makedirs(MEDIA_ROOT, exist_ok=True)

# En prod (Render) tu dominio será https://<tu-app>.onrender.com
CSRF_TRUSTED_ORIGINS = (
    os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS")
    else []
)
