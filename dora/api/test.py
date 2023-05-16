import json

from model_bakery import baker
from rest_framework.test import APITestCase

from dora.core.test_utils import make_service, make_structure
from dora.services.enums import ServiceStatus
from dora.services.models import ServiceKind, ServiceSubCategory
from dora.structures.models import (
    StructureNationalLabel,
    StructureSource,
    StructureTypology,
)


class PublicAPIStructureTestCase(APITestCase):
    def setUp(self):
        self.maxDiff = None
        baker.make("structures.StructureSource", value="solidagregateur")
        baker.make("structures.StructureNationalLabel", value="MOBIN")
        baker.make("structures.StructureNationalLabel", value="AFPA")

    def test_api_response(self):
        response = self.client.get("/api/v2/structures/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_serialization_exemple(self):
        # Example adapté de la doc data·inclusion :
        # https://www.data.inclusion.beta.gouv.fr/schemas-de-donnees-de-loffre/schema-des-structures-et-services-dinsertion
        typology = StructureTypology.objects.get(value="ASSO")
        source = StructureSource.objects.get(value="solidagregateur")
        parent = make_structure()

        struct = make_structure(
            siret="60487647500499",
            # rna="W123456789",
            name="MOBILETTE",
            city="Robinboeuf CEDEX",
            postal_code="09891",
            city_code="09890",
            address1="RUE DE LECLERCQ",
            address2="HOTEL DE VILLE",
            longitude=7.848133,
            latitude=48.7703,
            typology=typology,
            phone="0102030405",
            email="julie@example.net",
            url="https://www.asso-gonzalez.net/",
            short_desc="L’association Mobilette propose des solutions de déplacement aux personnes pour qui la non mobilité est un frein à l’insertion professionnelle : - connaissance de l'offre de transport du territoire - accès à un véhicule 2 ou 4 roues - transport solidaire - accès au permis",
            full_desc="",
            source=source,
            parent=parent,
            opening_hours='Mo-Fr 10:00-20:00 "sur rendez-vous"; PH off',
            accesslibre_url="https://acceslibre.beta.gouv.fr/app/29-lampaul-plouarzel/a/bibliotheque-mediatheque/erp/mediatheque-13/",
            other_labels=[
                "Nièvre médiation numérique",
            ],
        )
        struct.modification_date = "2022-04-28T16:53:11Z"
        struct.national_labels.add(
            StructureNationalLabel.objects.get(value="MOBIN"),
            StructureNationalLabel.objects.get(value="AFPA"),
        )
        s1 = make_service(structure=struct, status=ServiceStatus.PUBLISHED)
        s1.subcategories.add(
            ServiceSubCategory.objects.get(value="numerique--acceder-a-du-materiel")
        )
        s2 = make_service(structure=struct, status=ServiceStatus.PUBLISHED)
        s2.subcategories.add(
            ServiceSubCategory.objects.get(
                value="equipement-et-alimentation--acces-a-du-materiel-informatique"
            )
        )
        struct.save()
        response = self.client.get(f"/api/v2/structures/{struct.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            json.loads(response.content),
            {
                "accessibilite": "https://acceslibre.beta.gouv.fr/app/29-lampaul-plouarzel/a/bibliotheque-mediatheque/erp/mediatheque-13/",
                "adresse": "RUE DE LECLERCQ",
                "antenne": True,
                "code_insee": "09890",
                "code_postal": "09891",
                "commune": "Robinboeuf CEDEX",
                "complement_adresse": "HOTEL DE VILLE",
                "courriel": "julie@example.net",
                "date_maj": "2022-04-28T16:53:11Z",
                "horaires_ouverture": 'Mo-Fr 10:00-20:00 "sur rendez-vous"; PH off',
                "id": str(struct.id),
                "labels_autres": ["Nièvre médiation numérique"],
                "labels_nationaux": ["MOBIN", "AFPA"],
                "latitude": 48.7703,
                "lien_source": f"http://localhost:3000/structures/{struct.slug}",
                "longitude": 7.848133,
                "nom": "MOBILETTE",
                "presentation_detail": None,
                "presentation_resume": "L’association Mobilette propose des solutions de déplacement aux personnes pour qui la non mobilité est un frein à l’insertion professionnelle : - connaissance de l'offre de transport du territoire - accès à un véhicule 2 ou 4 roues - transport solidaire - accès au permis",
                "rna": None,
                # "rna": "W123456789",
                "siret": "60487647500499",
                "site_web": "https://www.asso-gonzalez.net/",
                "source": "solidagregateur",
                "telephone": "0102030405",
                "typologie": "ASSO",
            },
        )


class PublicAPIServiceTestCase(APITestCase):
    def setUp(self):
        self.maxDiff = None

    def test_api_response(self):
        response = self.client.get("/api/v2/services/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_unpublished_service_is_not_serialized(self):
        service = make_service(status=ServiceStatus.DRAFT)
        response = self.client.get(f"/api/v2/services/{service.id}/")
        self.assertEqual(response.status_code, 404)

    def test_serialization_exemple(self):
        # Example adapté de la doc data·inclusion :
        # https://www.data.inclusion.beta.gouv.fr/schemas-de-donnees-de-loffre/schema-des-structures-et-services-dinsertion
        structure = make_structure()
        service = make_service(
            structure=structure,
            name="TISF",
            short_desc="Accompagnement des familles à domicile",
            fee_details="",
            status=ServiceStatus.PUBLISHED,
        )
        service.subcategories.add(
            ServiceSubCategory.objects.get(value="numerique--acceder-a-du-materiel")
        )
        service.kinds.add(
            ServiceKind.objects.get(value="formation"),
            ServiceKind.objects.get(value="information"),
        )
        response = self.client.get(f"/api/v2/services/{service.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            json.loads(response.content),
            {
                "id": str(service.id),
                "structure_id": str(structure.id),
                "source": None,
                "nom": "TISF",
                "presentation_resume": "Accompagnement des familles à domicile",
                "types": [
                    "formation",
                    "information",
                ],
                "thematiques": ["numerique--acceder-a-du-materiel"],
                "prise_rdv": None,
                "frais": None,
                "frais_autres": None,
                "profils": None,
            },
        )

    def test_subcategories_other_excluded(self):
        # Example adapté de la doc data·inclusion :
        # https://www.data.inclusion.beta.gouv.fr/schemas-de-donnees-de-loffre/schema-des-structures-et-services-dinsertion
        structure = make_structure()
        service = make_service(
            structure=structure,
            name="TISF",
            short_desc="Accompagnement des familles à domicile",
            fee_details="",
            status=ServiceStatus.PUBLISHED,
        )
        service.subcategories.add(
            ServiceSubCategory.objects.get(value="numerique--acceder-a-du-materiel")
        )
        service.subcategories.add(
            ServiceSubCategory.objects.get(value="numerique--autre")
        )

        response = self.client.get(f"/api/v2/services/{service.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            json.loads(response.content),
            {
                "id": str(service.id),
                "structure_id": str(structure.id),
                "source": None,
                "nom": "TISF",
                "presentation_resume": "Accompagnement des familles à domicile",
                "types": [],
                "thematiques": ["numerique--acceder-a-du-materiel"],
                "prise_rdv": None,
                "frais": None,
                "frais_autres": None,
                "profils": None,
            },
        )
