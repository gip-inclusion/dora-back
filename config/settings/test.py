import os

import dj_database_url

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

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.0.1", "0.0.0.0"]
AUTH_PASSWORD_VALIDATORS = []

# Configuration nécessaire pour les tests :
SIB_ACTIVE = False
