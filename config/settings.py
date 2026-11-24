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
    "soggetti",
    "archivio",
    "elaborazione",
    "grafo",
    "indici",
    "oauth2_provider",
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

# App grafo: indirizzo con cui gli analisti raggiungono l'applicativo (per esempio
# https://controlli.ufficio.example). Serve a comporre i collegamenti alle mappe
# restituiti alla chat; se vuoto si usa l'indirizzo della richiesta ricevuta.
GRAFO_URL_PUBBLICO = os.environ.get("CONTROLLI_URL_PUBBLICO", "")

# Accesso OAuth 2.0 per la chat (app grafo, versione 21). L'applicativo è il server di
# autorizzazione: la chat si registra da sola, l'analista accede con il proprio utente
# e approva, la chat riceve un token legato a quell'utente e al solo servizio MCP.
OAUTH2_PROVIDER = {
    # Un solo ambito: interrogare l'analisi di rete (lo stesso nome è in grafo/contratto.py)
    "SCOPES": {"grafo": "Interrogare l'analisi di rete dalla chat a tuo nome"},
    "DEFAULT_SCOPES": ["grafo"],
    # Solo il flusso con codice di autorizzazione e PKCE; niente flussi sconsigliati
    "PKCE_REQUIRED": True,
    "OAUTH2_RESPONSE_TYPES_SUPPORTED": ["code"],
    "OAUTH2_GRANT_TYPES_SUPPORTED": ["authorization_code", "refresh_token"],
    "OAUTH2_TOKEN_ENDPOINT_AUTH_METHODS_SUPPORTED": ["none", "client_secret_post", "client_secret_basic"],
    # La chat si registra da sola come client (RFC 7591), senza credenziali: chiunque
    # raggiunga il server può registrarne uno, ma senza l'accesso e il consenso di un
    # utente un client non ottiene nulla. Da restringere prima dell'uso reale (TODO.md).
    "DCR_ENABLED": True,
    "DCR_REGISTRATION_PERMISSION_CLASSES": ("oauth2_provider.dcr.AllowAllDCRPermission",),
    # La pagina di consenso si mostra la prima volta; poi si salta finché l'utente ha un
    # token non scaduto per lo stesso programma. "force" la ripropone a ogni accesso.
    "REQUEST_APPROVAL_PROMPT": os.environ.get("CONTROLLI_OAUTH_CONSENSO", "auto"),
    # Una chat sullo stesso computer può ricevere la risposta su http://localhost:porta
    "ALLOW_LOCALHOST_LOOPBACK": True,
    # Durata del token della chat (ore) e del token di rinnovo (giorni)
    "ACCESS_TOKEN_EXPIRE_SECONDS": int(os.environ.get("CONTROLLI_OAUTH_ORE_TOKEN", "8")) * 3600,
    "REFRESH_TOKEN_EXPIRE_SECONDS": int(os.environ.get("CONTROLLI_OAUTH_GIORNI_RINNOVO", "7")) * 86400,
}

# Caricamento dei file (app archivio). Il contenuto dei file sta nel deposito, fuori
# dal repository; i limiti proteggono il server da caricamenti enormi.
ARCHIVIO_DEPOSITO = Path(os.environ.get("CONTROLLI_ARCHIVIO_DEPOSITO", MEDIA_ROOT / "archivio"))
ARCHIVIO_MASSIMO_BYTE_PER_FILE = int(os.environ.get("CONTROLLI_MASSIMO_MB_PER_FILE", "500")) * 1024 * 1024
ARCHIVIO_ZIP_MASSIMO_FILE = int(os.environ.get("CONTROLLI_ZIP_MASSIMO_FILE", "2000"))
ARCHIVIO_ZIP_MASSIMO_BYTE = int(os.environ.get("CONTROLLI_ZIP_MASSIMO_MB", "2048")) * 1024 * 1024
# Una cartella scelta dal browser arriva come tanti file in una sola richiesta:
# il limite predefinito di Django (100) è troppo basso.
DATA_UPLOAD_MAX_NUMBER_FILES = ARCHIVIO_ZIP_MASSIMO_FILE
# Ogni file porta con sé il campo del proprio percorso
DATA_UPLOAD_MAX_NUMBER_FIELDS = ARCHIVIO_ZIP_MASSIMO_FILE + 1000

# Elaborazione dei file (app elaborazione): lettura di scansioni e PDF con il modello
# locale. L'indirizzo predefinito è quello del server Unsloth in uso (127.0.0.0, non
# 127.0.0.1); la chiave si legge dalla variabile d'ambiente indicata, mai dal repository.
ELABORAZIONE_MODELLO_URL = os.environ.get("CONTROLLI_MODELLO_URL", "http://127.0.0.0:8888/v1")
ELABORAZIONE_MODELLO_NOME = os.environ.get("CONTROLLI_MODELLO_NOME", "unsloth/Qwen3-VL-8B-Thinking-GGUF")
ELABORAZIONE_MODELLO_VARIABILE_CHIAVE = "UNSLOTH_STUDIO_AUTH_TOKEN"
ELABORAZIONE_MODELLO_OPZIONI = {"reasoning_effort": "low"}
ELABORAZIONE_MODELLO_MASSIMO_TOKEN = int(os.environ.get("CONTROLLI_MODELLO_MASSIMO_TOKEN", "6000"))
ELABORAZIONE_PUNTI_PER_POLLICE = int(os.environ.get("CONTROLLI_PUNTI_PER_POLLICE", "200"))
ELABORAZIONE_MASSIMO_TENTATIVI = 3
# Identificativi e importi letti da una scansione aspettano la conferma di una persona,
# finché non si è misurato quanto sbaglia la trascrizione del modello (DECISIONI.md, n. 74)
ELABORAZIONE_RIVEDI_LE_SCANSIONI = os.environ.get("CONTROLLI_RIVEDI_LE_SCANSIONI", "1") == "1"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
