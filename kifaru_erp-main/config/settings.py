# config/settings.py

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ── SECURITY ────────────────────────────────────────────────────────────────
# On Render, SECRET_KEY is set as an Environment Variable. Never hardcode it.
SECRET_KEY = os.environ.get('SECRET_KEY', 'local-dev-fallback-key-change-this')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.onrender.com',  # Covers all *.onrender.com subdomains automatically
    os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''),
    '.up.railway.app', # <-- ADD THIS for Railway subdomains
    os.environ.get('RAILWAY_PUBLIC_DOMAIN', ''), # <-- ADD THIS (Railway injects this automatically)
]

# While you are here, let's also allow CSRF for Railway:
CSRF_TRUSTED_ORIGINS =[
    f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'localhost')}"
]


# ── APPS ────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Kifaru ERP Modules
    'core',
    'accounting',
    'inventory',
    'purchasing',
    'sales',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <-- WhiteNoise: serves static files on Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ── DATABASE ─────────────────────────────────────────────────────────────────
# On Render, DATABASE_URL is automatically injected when you attach a Postgres DB.
# Locally, it falls back to your existing Postgres config.
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # This runs on RAILWAY (PostgreSQL)
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # This runs locally in your GITHUB CODESPACE (SQLite)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ── STATIC FILES ─────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Auth redirects
LOGIN_URL          = '/admin/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/admin/login/'

# WhiteNoise compression + caching for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ── INTERNATIONALISATION ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Africa/Nairobi'
USE_I18N      = True
USE_TZ        = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── SECURITY HEADERS (active only in production) ─────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT          = True
    SESSION_COOKIE_SECURE        = True
    CSRF_COOKIE_SECURE           = True
    SECURE_HSTS_SECONDS          = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER      = ('HTTP_X_FORWARDED_PROTO', 'https')
