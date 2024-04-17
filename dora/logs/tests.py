import logging

import pytest
from django.core.exceptions import ValidationError

from .core import ActionLogHandler
from .models import ActionLog

# inutile de tester les fonctions héritées de logging.Logger et logging.Handler (filtre, niveau ...)


@pytest.fixture
def logger():
    return logging.getLogger("dora.logs.core")


def test_logger_created(logger):
    # le logger 'dora.logs.core' doit exister et avoir le bon handler
    [handler] = logger.handlers

    assert isinstance(handler, ActionLogHandler)


def test_clean_log_record(logger):
    # la méthode save() effectue un clean()
    with pytest.raises(ValidationError):
        ActionLog().clean()

    with pytest.raises(ValidationError):
        ActionLog(payload={"msg": "ko"}).clean()

    with pytest.raises(ValidationError):
        ActionLog(payload={"level": "ERROR"}).clean()

    with pytest.raises(ValidationError):
        ActionLog(payload={"msg": "ok", "level": "MY_LEVEL"}).clean()

    ActionLog(payload={"msg": "ok", "level": "INFO"}).clean()


def test_store_log(logger):
    ActionLog(
        payload={"msg": "ok", "level": "DEBUG", "myInt": 42, "myBool": True}
    ).save()

    result = ActionLog.objects.first()

    assert result
    assert result.payload.get("msg") == "ok"
    assert result.payload.get("level") == "DEBUG"
    assert result.payload.get("myInt") == 42
    assert result.payload.get("myBool")


def test_log_me(logger):
    logger.critical("Message important", {"unParam": "au hasard"})

    result = ActionLog.objects.first()

    assert result
    assert result.payload.get("msg") == "Message important"
    assert result.payload.get("level") == "CRITICAL"
    assert result.payload.get("unParam") == "au hasard"
