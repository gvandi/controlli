"""Impostazioni del progetto.

I valori che cambiano tra un'installazione e l'altra (chiave segreta, database)
si leggono dall'ambiente o dal file .env nella cartella del progetto.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _carica_env(percorso):
    """Legge un file .env semplice (CHIAVE=valore) senza dipendenze esterne."""
    if not percorso.exists():
        return
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        chiave, valore = riga.split("=", 1)
        os.environ.setdefault(chiave.strip(), valore.strip())


_carica_env(BASE_DIR / ".env")

DEBUG = os.environ.get("CONTROLLI_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("CONTROLLI_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("CONTROLLI_SECRET_KEY non impostata: vedi .env.example")
    SECRET_KEY = "chiave-solo-per-sviluppo"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("CONTROLLI_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "utenti",
    "decodifiche",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("CONTROLLI_DB_NAME", "controlli"),
        "USER": os.environ.get("CONTROLLI_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("CONTROLLI_DB_PASSWORD", ""),
        "HOST": os.environ.get("CONTROLLI_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("CONTROLLI_DB_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "utenti.Utente"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# La sessione scade dopo 30 minuti di inattività.
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True

# Lingua unica: italiano. I testi dell'interfaccia sono marcati come traducibili;
# per aggiungere una lingua basta elencarla qui e fornire la traduzione in locale/
# (DECISIONI.md, n. 29).
LANGUAGE_CODE = "it"
LANGUAGES = [("it", "Italiano")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# File caricati dagli utenti: restano sul server, fuori dal repository.
MEDIA_ROOT = BASE_DIR / "dati_caricati"
MEDIA_URL = "dati_caricati/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
