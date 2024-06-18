import os

import dj_database_url

from . import BASE_DIR

# Contrairement aux environements de production et staging,
# les environnement de développement et de test se basent sur les fichiers
# de configuration du répertoire 'envs'.
if os.path.isdir(BASE_DIR / "envs"):
    import environ

    environ.Env.read_env(os.path.join(BASE_DIR / "envs", "dev.env"))
    environ.Env.read_env(os.path.join(BASE_DIR / "envs", "secrets.env"))
else:
    raise Exception("Impossible de charger la configuration des envrionnements")

from .base import *  # noqa F403

DEBUG = True

# Base de données :
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

if DATABASE_URL := os.environ.get("DATABASE_URL"):
    # utilisation de DATABASE_URL si défini, mais sans SSL
    DATABASES = {"default": dj_database_url.config()}
else:
    # sinon configuration "traditionnelle" de postgres
    DATABASES = {
        "default": {
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ["POSTGRES_USER"],
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ["POSTGRES_PORT"],
        }
    }

# Ne pas oublier de redéfinir le moteur après une modification de config DB
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

# Django extensions :
INSTALLED_APPS += ["django_extensions"]  # noqa F405
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
] + MIDDLEWARE  # noqa F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.0.1", "0.0.0.0"]
AUTH_PASSWORD_VALIDATORS = []

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (  # noqa F405
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# Profiling :
# utilisation de Silk (configurable via var env)
PROFILE = os.environ.get("DJANGO_PROFILE") == "true"

if DEBUG and PROFILE:
    SILKY_PYTHON_PROFILER = True
    INSTALLED_APPS.append("silk")  # noqa F405
    MIDDLEWARE = [
        "silk.middleware.SilkyMiddleware",
        "querycount.middleware.QueryCountMiddleware",
    ] + MIDDLEWARE  # noqa
    QUERYCOUNT = {
        "IGNORE_SQL_PATTERNS": [r"silk_"],
        "IGNORE_REQUEST_PATTERNS": [r"/silk/"],
    }
    CSP_EXCLUDE_URL_PREFIXES += ("/silk/",)  # noqa F405

# TODO: nécessaire sur staging ?
# ce paramètre n'était fixé que pour les environnement *HORS* production
# Q : est-ce c'est justifié pour staging ?
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "django": {
            "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
        },
    },
}
