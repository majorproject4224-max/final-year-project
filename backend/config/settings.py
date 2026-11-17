"""Settings for personal-laptop development, Codespaces and Render."""
import os
import sys
from datetime import timedelta
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY and DEBUG:
    SECRET_KEY = "development-only-secret-not-for-deployment"
if not SECRET_KEY or (not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("replace-"))):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY; production needs a random value of at least 50 characters.")

def env_list(name, default=""):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173/")
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
if os.getenv("CODESPACE_NAME"):
    preview_host = f"{os.environ['CODESPACE_NAME']}-5173.{os.getenv('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'app.github.dev')}"
    CORS_ALLOWED_ORIGINS.append(f"https://{preview_host}")
    ALLOWED_HOSTS.append(preview_host)
WEBSOCKET_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
INSTALLED_APPS = ["daphne", "django_mongodb_backend", "rest_framework", "corsheaders", "config.apps.MongoAuthConfig", "config.apps.MongoContentTypesConfig", "platform_api.apps.PlatformApiConfig"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "corsheaders.middleware.CorsMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True, "OPTIONS": {}}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/?replicaSet=rs0")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "connect_ai")
DATABASES = {"default": {"ENGINE": "django_mongodb_backend", "HOST": MONGODB_URI, "NAME": MONGODB_DATABASE}}
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["platform_api.authentication.MongoJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["platform_api.parsers.ObjectJSONParser"],
    "EXCEPTION_HANDLER": "platform_api.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {"anon": "120/hour", "user": "3000/hour", "auth": "20/hour"},
}
if os.getenv("API_THROTTLING_ENABLED", "1") == "1":
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"]
SIMPLE_JWT = {"ACCESS_TOKEN_LIFETIME": timedelta(minutes=15), "REFRESH_TOKEN_LIFETIME": timedelta(days=7)}
REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": [REDIS_URL], "capacity": 100, "expiry": 30}}}
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL, "KEY_PREFIX": "connect"}}
else:
    if not DEBUG:
        raise ImproperlyConfigured("Set REDIS_URL for deployed chat and shared rate limiting.")
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "0" if DEBUG else "1") == "1"
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
ML_MODEL_PATH = Path(os.getenv("ML_MODEL_PATH", str(PROJECT_ROOT / "ml/models/recommender.joblib")))
