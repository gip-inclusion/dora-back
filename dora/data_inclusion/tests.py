import unittest

from rest_framework.test import APITestCase

from dora import data_inclusion
from django.conf import settings


class DataInclusionIntegrationTestCase(APITestCase):
    def setUp(self):
        self.di_client = data_inclusion.DataInclusionClient(
            base_url=settings.DATA_INCLUSION_URL,
            token=settings.DATA_INCLUSION_API_KEY,
        )

    @unittest.skipUnless(
        settings.ENVIRONMENT == "local",  # TODO: need a more accurate condition
        "3rd party probably not available",
    )
    def test_search_services(self):
        self.di_client.search_services(
            code_insee="91223",
            thematiques=["mobilite--comprendre-et-utiliser-les-transports-en-commun"],
        )
