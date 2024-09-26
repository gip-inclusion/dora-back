import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _use_db(db):
    # Active automatiquement la gestion de la db
    # (ce qui n'est pas fait par défaut avec pytest).
    pass


@pytest.fixture
def api_client():
    return APIClient()
