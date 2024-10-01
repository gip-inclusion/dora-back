"""
Django settings for dora project.

Generated by 'django-admin startproject' using Django 3.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os

from corsheaders.defaults import default_headers

from . import BASE_DIR

# Paramètres Django
# Voir : https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

# Liste des applications Django :
# peut-être étendue ou complétée par les profils de dev ou test.
INSTALLED_APPS = [
    "django.contrib.gis",
    "django.contrib.auth",
    # OIDC / ProConnect : doit être chargé après `django.contrib.auth`
    "mozilla_django_oidc",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django_filters",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_gis",
    "corsheaders",
    # local / DORA
    "config.apps.AdminConfig",
    "dora.core",
    "dora.rest_auth",
    "dora.users",
    "dora.structures",
    "dora.services",
    "dora.orientations",
    "dora.service_suggestions",
    "dora.sirene",
    "dora.support",
    "dora.admin_express",
    "dora.stats",
    "dora.notifications",
    "dora.logs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    # Rafraichissement du token ProConnect
    "mozilla_django_oidc.middleware.SessionRefresh",
]

# OIDC / ProConnect
AUTHENTICATION_BACKENDS = [
    "dora.oidc.OIDCAuthenticationBackend",
]

# Permet de garder le comportement d'identification "standard" (e-mail/password)
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "email"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": [
                "dora.core.templatetags.globals",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_USER_MODEL = "users.User"

# Base de données :
# Si la connexion est déjà définie de cette manière, on la réutilise.
# Sinon, elle sera définie dans les différents fichiers de settings
# (via les variables d'environnement `PG_xxx` standards).
DATABASE_URL = os.getenv("DATABASE_URL")

# Cache :
# https://docs.djangoproject.com/en/4.2/topics/cache/

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL"),
        "TIMEOUT": None,
    }
}

# Hôtes autorisés :
# https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/#allowed-hosts

ALLOWED_HOSTS = (
    os.getenv("DJANGO_ALLOWED_HOSTS").split(",")
    if os.getenv("DJANGO_ALLOWED_HOSTS")
    else None
)


# Validation des mot de passe :
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {
            "user_attributes": ["first_name", "last_name", "email"],
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# I18N :
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_TZ = True

# Fichier statiques (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Téléversement de fichiers
# https://django-storages.readthedocs.io/en/latest/backends/azure.html

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Stockage S3 CleverCloud :
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_QUERYSTRING_EXPIRE = 24 * 3600  # secondes

MAX_UPLOAD_SIZE_MB = 6
ALLOWED_UPLOADED_FILES_EXTENSIONS = [
    "doc",
    "docx",
    "pdf",
    "png",
    "jpeg",
    "jpg",
    "odt",
    "xls",
    "xlsx",
]

# Type de clé primaire par défaut :
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging :
# permet un niveau de log 'INFO' pour le logger `dora.logs.core`,
# qui est également réglable via variable d'environnement, si besoin
# (le reste de la configuration de logging par défaut n'est pas modifié).
# Concernant Django, avoir des logs visibles à certains point critiques
# de la configuration peut être une bonne idée.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "django": {
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "dora.logs.core": {
            "level": os.getenv("DORA_LOGS_CORE_LEVEL", "INFO"),
        },
    },
}


# Rest Framework :
# https://www.django-rest-framework.org/api-guide/settings/

REST_FRAMEWORK = {
    # Let's lock down access by default
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAdminUser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    # Camel Case
    # https://github.com/vbabiy/djangorestframework-camel-case
    "DEFAULT_RENDERER_CLASSES": (
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "djangorestframework_camel_case.parser.CamelCaseFormParser",
        "djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
    ),
    "JSON_UNDERSCOREIZE": {
        "no_underscore_before_number": True,
    },
    "EXCEPTION_HANDLER": "dora.core.exceptions_handler.custom_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# CORS :
# https://github.com/adamchainz/django-cors-headers/blob/main/README.rst
CORS_ALLOWED_ORIGIN_REGEXES = [os.getenv("DJANGO_CORS_ALLOWED_ORIGIN_REGEXES")]
CORS_ALLOW_HEADERS = list(default_headers) + [
    "sentry-trace",
]


# Configuration spécifique de l'application DORA :

# Services :
DEFAULT_SEARCH_RADIUS = 15  # in km
RECENT_SERVICES_CUTOFF_DAYS = 30

# Bot user :
DORA_BOT_USER = "dora-bot@dora.beta.gouv.fr"

# Authentifications tierces parties :
PE_CLIENT_ID = os.getenv("PE_CLIENT_ID")
PE_CLIENT_SECRET = os.getenv("PE_CLIENT_SECRET")

# Compte utilisateur Data·Inclusion
DATA_INCLUSION_EMAIL = "data.inclusion@beta.gouv.fr"
DATA_INCLUSION_URL = os.getenv("DATA_INCLUSION_URL")
DATA_INCLUSION_IMPORT_API_KEY = os.getenv("DATA_INCLUSION_IMPORT_API_KEY")
DATA_INCLUSION_STREAM_API_KEY = os.getenv("DATA_INCLUSION_STREAM_API_KEY")
DATA_INCLUSION_STREAM_SOURCES = (lambda s: s.split(",") if s else None)(
    os.getenv("DATA_INCLUSION_STREAM_SOURCES")
)
DATA_INCLUSION_TIMEOUT_SECONDS = os.getenv("DATA_INCLUSION_TIMEOUT_SECONDS")
SKIP_DI_INTEGRATION_TESTS = True

# Send In Blue :
SIB_ACTIVE = os.getenv("SIB_ACTIVE") == "true"
SIB_API_KEY = os.getenv("SIB_API_KEY")
SIB_ONBOARDING_LIST = os.getenv("SIB_ONBOARDING_LIST")
SIB_ONBOARDING_PUTATIVE_MEMBER_LIST = os.getenv("SIB_ONBOARDING_PUTATIVE_MEMBER_LIST")
SIB_ONBOARDING_MEMBER_LIST = os.getenv("SIB_ONBOARDING_MEMBER_LIST")

# Actualisation des services :
NUM_DAYS_BEFORE_ADVISED_SERVICE_UPDATE = 30 * 6
NUM_DAYS_BEFORE_MANDATORY_SERVICE_UPDATE = 30 * 8

# Modération :
MATTERMOST_HOOK_KEY = os.getenv("MATTERMOST_HOOK_KEY")

# INCLUSION-CONNECT
IC_ISSUER_ID = os.getenv("IC_ISSUER_ID")
IC_AUTH_URL = os.getenv("IC_AUTH_URL")
IC_TOKEN_URL = os.getenv("IC_TOKEN_URL")
IC_LOGOUT_URL = os.getenv("IC_LOGOUT_URL")
IC_ACCOUNT_URL = os.getenv("IC_ACCOUNT_URL")
IC_CLIENT_ID = os.getenv("IC_CLIENT_ID")
IC_CLIENT_SECRET = os.getenv("IC_CLIENT_SECRET")

# OIDC / PROCONNECT
PC_CLIENT_ID = os.getenv("PC_CLIENT_ID")
PC_CLIENT_SECRET = os.getenv("PC_CLIENT_SECRET")
PC_DOMAIN = os.getenv("PC_DOMAIN", "fca.integ01.dev-agentconnect.fr")
PC_ISSUER = os.getenv("PC_ISSUER", f"{PC_DOMAIN}/api/v2")
PC_AUTHORIZE_PATH = os.getenv("PC_AUTHORIZE_PATH", "authorize")
PC_TOKEN_PATH = os.getenv("PC_TOKEN_PATH", "token")
PC_USERINFO_PATH = os.getenv("PC_USERINFO_PATH", "userinfo")

# mozilla_django_oidc:
OIDC_RP_CLIENT_ID = os.getenv("PC_CLIENT_ID")
OIDC_RP_CLIENT_SECRET = os.getenv("PC_CLIENT_SECRET")
OIDC_RP_SCOPES = "openid given_name usual_name email siret custom uid"

# Nécessaire pour la gestion de la fin de session
OIDC_STORE_ID_TOKEN = True
ALLOW_LOGOUT_GET_METHOD = True

# obligatoire pour ProConnect: à passer en paramètre de requête supplémentaire
OIDC_AUTH_REQUEST_EXTRA_PARAMS = {"acr_values": "eidas1"}

# mozilla_django_oidc n'utilise pas de discovery / .well-known
# on définit donc chaque endpoint
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_OP_JWKS_ENDPOINT = f"https://{PC_ISSUER}/jwks"
OIDC_OP_AUTHORIZATION_ENDPOINT = f"https://{PC_ISSUER}/authorize"
OIDC_OP_TOKEN_ENDPOINT = f"https://{PC_ISSUER}/token"
OIDC_OP_USER_ENDPOINT = f"https://{PC_ISSUER}/userinfo"
OIDC_OP_LOGOUT_ENDPOINT = f"https://{PC_ISSUER}/session/end"

# Intervalle de rafraichissement du token (4h)
OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 4 * 60 * 60

# Redirection vers le front DORA en cas de succès de l'identification
LOGIN_REDIRECT_URL = "/oidc/logged_in/"
OIDC_CALLBACK_CLASS = "dora.oidc.views.CustomAuthorizationCallbackView"

# Recherches sauvegardées :
INCLUDES_DI_SERVICES_IN_SAVED_SEARCH_NOTIFICATIONS = (
    os.getenv("INCLUDES_DI_SERVICES_IN_SAVED_SEARCH_NOTIFICATIONS") == "true"
)

# Notifications :
# voir management command `process_notification_tasks`

# activation des notifications
NOTIFICATIONS_ENABLED = os.getenv("NOTIFICATIONS_ENABLED", "") == "true"

# si défini, seules ces tâches de notification seront lancées par le CRON
# même principe que pour la management command, les tâches sélectionnées sont séparées par des ","
NOTIFICATIONS_TASK_TYPES = os.getenv("NOTIFICATIONS_TASK_TYPES", "")

# nombre de Notifications à envoyer pour chaque tâche
try:
    NOTIFICATIONS_LIMIT = int(os.getenv("NOTIFICATIONS_LIMIT", 0))
except Exception:
    NOTIFICATIONS_LIMIT = 0

# ces paramètres ne sont pas liés au système de notification
NUM_DAYS_BEFORE_DRAFT_SERVICE_NOTIFICATION = 7
NUM_DAYS_BEFORE_ORIENTATIONS_NOTIFICATION = 10

# GDAL :
if "GDAL_LIBRARY_PATH" in os.environ:
    GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH")
if "GEOS_LIBRARY_PATH" in os.environ:
    GEOS_LIBRARY_PATH = os.getenv("GEOS_LIBRARY_PATH")

# DJANGO_ADMINS=Name1:email1,Name2:email2
ADMINS = (
    [u.split(":") for u in os.getenv("DJANGO_ADMINS").split(",")]
    if os.getenv("DJANGO_ADMINS")
    else None
)

# CSP :
# règles pour l'admin et les versions d'API
PUBLIC_API_VERSIONS = ["1", "2"]
CSP_EXCLUDE_URL_PREFIXES = (
    "/admin/",
    *[f"/api/v{version}/schema/doc/" for version in PUBLIC_API_VERSIONS],
)

# Envoi d'e-mails transactionnels :
# https://app.tipimail.com/#/app/settings/smtp_and_apis
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
NO_REPLY_EMAIL = os.getenv("NO_REPLY_EMAIL", DEFAULT_FROM_EMAIL)
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USE_TLS = True
EMAIL_DOMAIN = os.getenv("EMAIL_DOMAIN")
FRONTEND_URL = os.getenv("FRONTEND_URL")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL")

SUPPORT_LINK = "https://aide.dora.inclusion.beta.gouv.fr"

# Rientations :
ORIENTATION_SUPPORT_LINK = os.getenv("ORIENTATION_SUPPORT_LINK")
ORIENTATION_EMAILS_DEBUG = os.getenv("ORIENTATION_EMAILS_DEBUG") == "true"
ORIENTATION_SIRENE_BLACKLIST = [
    # Pole Emploi / France Travail
    "130005481",
    # CAF
    "779311224",
    "534155403",
    "775548555",
    "775549371",
    "782437586",
    "782620520",
    "534224282",
    "780254702",
    "776656209",
    "780349759",
    "775555642",
    "776744005",
    "775558364",
    "775561343",
    "775562531",
    "781172366",
    "775564669",
    "775021801",
    "777927138",
    "778213348",
    "777461336",
    "777998881",
    "303336192",
    "778274613",
    "778297242",
    "534738778",
    "775573397",
    "780808010",
    "775103955",
    "535326656",
    "775915085",
    "776950446",
    "776986671",
    "781847488",
    "534089529",
    "777749375",
    "775189038",
    "775347875",
    "535363071",
    "778422832",
    "782099121",
    "775369598",
    "534216080",
    "779145598",
    "786019554",
    "775513708",
    "777053125",
    "782152888",
    "776115255",
    "534172481",
    "780860292",
    "780428975",
    "775613227",
    "775613995",
    "775615529",
    "783382344",
    "777907700",
    "780004032",
    "778477737",
    "775622335",
    "775624588",
    "775627383",
    "783806110",
    "534175179",
    "534224613",
    "775629256",
    "783911951",
    "534214051",
    "775634264",
    "831358262",
    "777169046",
    "775640238",
    "778868497",
    "778953844",
    "534037254",
    "778542837",
    "778600130",
    "786338871",
    "775653330",
    "776531576",
    "380992255",
    "534092499",
    "784971343",
    "381067784",
    "781459599",
    "775710791",
    "777187691",
    "777306184",
    "783169196",
    "775714124",
    "786448050",
    "775716202",
    "778073189",
    "775717333",
    "778649525",
    "778714964",
    "381016534",
    "381050996",
    "380980300",
    "381202282",
    "381002534",
    "782993133",
    "327398152",
    "314560822",
    "314307828",
    "315190751",
    "314635368",
]

# Environnement :
# production | staging | local
# Utilisé our l'affichage de l'environnement sur l'admin,
# et pour activer le SSL sur la connexion à la base de données.
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

# Profiling (Silk) :
# Doit être explicitement activé (via env var)
PROFILE = False
