import os

from .settings import *  # noqa

IS_TESTING = True
SECRET_KEY = "foobar"
DATABASES = {
    "default": {
        "NAME": os.environ.get("POSTGRES_DB", "dora"),
        "USER": os.environ.get("POSTGRES_USER", "dora"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "dora"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "ENGINE":"django.contrib.gis.db.backends.postgis",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379"),
        "TIMEOUT": None,
    }
}
