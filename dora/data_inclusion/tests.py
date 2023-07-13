import unittest

from django.conf import settings
from rest_framework.test import APITestCase

from dora import data_inclusion


class DataInclusionIntegrationTestCase(APITestCase):
    """These integration-level tests check the connection to data.inclusion.

    They depend on the data.inclusion api and should not be run
    systematically, because of their inherent high cost and instability.
    """

    def setUp(self):
        self.di_client = data_inclusion.di_client_factory()

    @unittest.skipIf(
        settings.SKIP_DI_INTEGRATION_TESTS, "data.inclusion api not available"
    )
    def test_search_services(self):
        self.di_client.search_services(
            code_insee="91223",
            thematiques=["mobilite--comprendre-et-utiliser-les-transports-en-commun"],
        )

    @unittest.skipIf(
        settings.SKIP_DI_INTEGRATION_TESTS, "data.inclusion api not available"
    )
    def test_list_services(self):
        self.di_client.list_services(source="dora")

    @unittest.skipIf(
        settings.SKIP_DI_INTEGRATION_TESTS, "data.inclusion api not available"
    )
    def test_retrieve_service(self):
        services = self.di_client.list_services(source="dora")

        self.di_client.retrieve_service(
            source="dora",
            id=services[0]["id"],
        )
