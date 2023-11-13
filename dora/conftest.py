import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def setup_test_settings(settings):
    # La fixture `settings` remets en place les settings en fin de session de test
    # en remplacement de l'ancien test runner
    settings.SIB_ACTIVE = False
    settings.IS_TESTING = True
    yield


@pytest.fixture(autouse=True)
def _use_db(db):
    # active automatiquement la gestion de la db
    # (ce qui n'est pas fait par défaut par pytest)
    pass


@pytest.fixture
def api_client():
    return APIClient()
