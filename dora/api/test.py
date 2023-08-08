import json

from django.conf import settings
from django.contrib.gis.geos import Point
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.admin_express.models import City, Department
from dora.core.test_utils import make_service, make_structure
from dora.services.enums import ServiceStatus
from dora.services.models import (
    BeneficiaryAccessMode,
    CoachOrientationMode,
    ConcernedPublic,
    Credential,
    LocationKind,
    Requirement,
    ServiceFee,
    ServiceKind,
    ServiceSubCategory,
)
from dora.structures.models import (
    StructureNationalLabel,
    StructureSource,
    StructureTypology,
)


class PublicAPIStructureTestCase(APITestCase):
    def setUp(self):
        self.di_user = baker.make(
            "users.User", is_valid=True, email=settings.DATA_INCLUSION_EMAIL
        )
        self.maxDiff = None
        baker.make("structures.StructureSource", value="solidagregateur")
        baker.make("structures.StructureNationalLabel", value="MOBIN")
        baker.make("structures.StructureNationalLabel", value="AFPA")
        baker.make("City", name="Robinboeuf CEDEX", code="09890")

    def test_api_response_need_di_user(self):
        response = self.client.get("/api/v2/structures/")
        self.assertEqual(response.status_code, 401)

    def test_api_response(self):
        self.client.force_authenticate(user=self.di_user)
        response = self.client.get("/api/v2/structures/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_serialization_exemple(self):
        self.client.force_authenticate(user=self.di_user)
        # Example adapté de la doc data·inclusion :
        # https://www.data.inclusion.beta.gouv.fr/schemas-de-donnees-de-loffre/schema-des-structures-et-services-dinsertion
        typology = StructureTypology.objects.get(value="ASSO")
        source = StructureSource.objects.get(value="solidagregateur")
        parent = make_structure()

        struct = make_structure(
            siret="60487647500499",
            # rna="W123456789",
            name="MOBILETTE",
            # city="Robinboeuf CEDEX",
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
                "siret": "60487647500499",
                "site_web": "https://www.asso-gonzalez.net/",
                "source": "solidagregateur",
                "telephone": "0102030405",
                "thematiques": None,
                "typologie": "ASSO",
            },
        )


class PublicAPIServiceTestCase(APITestCase):
    def setUp(self):
        self.maxDiff = None
        self.di_user = baker.make(
            "users.User", is_valid=True, email=settings.DATA_INCLUSION_EMAIL
        )

    def test_api_response(self):
        self.client.force_authenticate(user=self.di_user)
        response = self.client.get("/api/v2/services/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_api_response_need_di_user(self):
        response = self.client.get("/api/v2/services/")
        self.assertEqual(response.status_code, 401)

    def test_unpublished_service_is_not_serialized(self):
        self.client.force_authenticate(user=self.di_user)
        service = make_service(status=ServiceStatus.DRAFT)
        response = self.client.get(f"/api/v2/services/{service.id}/")
        self.assertEqual(response.status_code, 404)

    def test_serialization_exemple(self):
        self.client.force_authenticate(user=self.di_user)
        # Example adapté de la doc data·inclusion :
        # https://www.data.inclusion.beta.gouv.fr/schemas-de-donnees-de-loffre/schema-des-structures-et-services-dinsertion
        baker.make(Department, code="29", name="Finistère")
        baker.make(City, code="29188", name="Plougasnou")

        structure = make_structure()
        service = make_service(
            structure=structure,
            status=ServiceStatus.PUBLISHED,
            name="TISF",
            short_desc="Accompagnement des familles à domicile",
            full_desc="Service de proximité visant à soutenir les familles ayant la responsabilité de jeunes enfants, en particulier les familles monoparentales.",
            fee_condition=ServiceFee.objects.get(value="payant"),
            fee_details="10 €",
            diffusion_zone_type="department",
            diffusion_zone_details="29",
            address1="25 route de Morlaix",
            city_code="29188",
            postal_code="29630",
            contact_name="Prénom Nom",
            contact_email="contact@alys.fr",
            contact_phone="0278911262",
            is_contact_info_public=True,
            publication_date="2023-02-04T12:34:44Z",
            modification_date="2023-03-11T16:54:10Z",
            geom=Point(3.76855, 23.88654, srid=4326),
            recurrence="Tu 09:00-12:00;We 14:00-17:00",
        )

        service.subcategories.add(
            ServiceSubCategory.objects.get(value="numerique--acceder-a-du-materiel")
        )
        service.kinds.add(
            ServiceKind.objects.get(value="formation"),
            ServiceKind.objects.get(value="information"),
        )
        service.concerned_public.add(
            baker.make(ConcernedPublic, name="adultes"),
            baker.make(ConcernedPublic, name="jeunes-16-26"),
            baker.make(ConcernedPublic, name="femmes"),
        )
        service.location_kinds.add(LocationKind.objects.get(value="en-presentiel"))
        service.location_kinds.add(LocationKind.objects.get(value="a-distance"))
        service.requirements.add(
            baker.make(
                Requirement, name="Bonne connaissance du français oral et écrit"
            ),
        )
        service.credentials.add(
            baker.make(
                Credential, name="Carte d'identité, passeport ou permis de séjour"
            ),
        )
        service.coach_orientation_modes.add(
            CoachOrientationMode.objects.get(value="envoyer-courriel"),
            CoachOrientationMode.objects.get(value="envoyer-formulaire"),
            CoachOrientationMode.objects.get(value="envoyer-fiche-prescription"),
        )
        service.beneficiaries_access_modes.add(
            BeneficiaryAccessMode.objects.get(value="envoyer-courriel")
        )

        response = self.client.get(f"/api/v2/services/{service.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            json.loads(response.content),
            {
                "adresse": "25 route de Morlaix",
                "code_insee": "29188",
                "code_postal": "29630",
                "commune": "Plougasnou",
                "complement_adresse": None,
                "contact_nom": "Prénom Nom",
                "contact_prenom": None,
                "contact_public": True,
                "courriel": "contact@alys.fr",
                "cumulable": True,
                "date_creation": "2023-02-04T12:34:44Z",
                "date_maj": "2023-03-11T16:54:10Z",
                "date_suspension": None,
                "formulaire_en_ligne": None,
                "frais_autres": "10 €",
                "frais": "payant",
                "id": str(service.id),
                "justificatifs": "Carte d'identité, passeport ou permis de séjour",
                "latitude": 23.88654,
                "lien_source": f"http://localhost:3000/services/{service.slug}",
                "longitude": 3.76855,
                "modes_accueil": ["a-distance", "en-presentiel"],
                "nom": "TISF",
                "pre_requis": "Bonne connaissance du français oral et écrit",
                "presentation_detail": "Service de proximité visant à soutenir les familles ayant la responsabilité de jeunes enfants, en particulier les familles monoparentales.",
                "presentation_resume": "Accompagnement des familles à domicile",
                "prise_rdv": None,
                "profils": ["adultes", "jeunes-16-26", "femmes"],
                "recurrence": "Tu 09:00-12:00;We 14:00-17:00",
                "source": None,
                "structure_id": str(structure.id),
                "telephone": "0278911262",
                "thematiques": ["numerique--acceder-a-du-materiel"],
                "types": [
                    "formation",
                    "information",
                ],
                "zone_diffusion_code": "29",
                "zone_diffusion_nom": "Finistère",
                "zone_diffusion_type": "departement",
                "modes_orientation_accompagnateur": [
                    "completer-le-formulaire-dadhesion",
                    "envoyer-un-mail",
                    "envoyer-un-mail-avec-une-fiche-de-prescription",
                ],
                "modes_orientation_beneficiaire": ["envoyer-un-mail"],
            },
        )

    def test_serialization_exemple_need_di_user(self):
        baker.make(Department, code="29", name="Finistère")
        baker.make(City, code="29188", name="Plougasnou")

        structure = make_structure()
        service = make_service(
            structure=structure,
            status=ServiceStatus.PUBLISHED,
            name="TISF",
            short_desc="Accompagnement des familles à domicile",
            full_desc="Service de proximité visant à soutenir les familles ayant la responsabilité de jeunes enfants, en particulier les familles monoparentales.",
            fee_condition=ServiceFee.objects.get(value="payant"),
            fee_details="10 €",
            diffusion_zone_type="department",
            diffusion_zone_details="29",
            address1="25 route de Morlaix",
            city_code="29188",
            postal_code="29630",
            contact_name="Prénom Nom",
            contact_email="contact@alys.fr",
            contact_phone="0278911262",
            is_contact_info_public=True,
            publication_date="2023-02-04T12:34:44Z",
            modification_date="2023-03-11T16:54:10Z",
            geom=Point(3.76855, 23.88654, srid=4326),
            recurrence="Tu 09:00-12:00;We 14:00-17:00",
        )

        service.subcategories.add(
            ServiceSubCategory.objects.get(value="numerique--acceder-a-du-materiel")
        )
        service.kinds.add(
            ServiceKind.objects.get(value="formation"),
            ServiceKind.objects.get(value="information"),
        )
        service.concerned_public.add(
            baker.make(ConcernedPublic, name="adultes"),
            baker.make(ConcernedPublic, name="jeunes-16-26"),
            baker.make(ConcernedPublic, name="femmes"),
        )
        service.location_kinds.add(LocationKind.objects.get(value="en-presentiel"))
        service.location_kinds.add(LocationKind.objects.get(value="a-distance"))
        service.requirements.add(
            baker.make(
                Requirement, name="Bonne connaissance du français oral et écrit"
            ),
        )
        service.credentials.add(
            baker.make(
                Credential, name="Carte d'identité, passeport ou permis de séjour"
            ),
        )

        response = self.client.get(f"/api/v2/services/{service.id}/")
        self.assertEqual(response.status_code, 401)

    def test_subcategories_other_excluded(self):
        self.client.force_authenticate(user=self.di_user)
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
        self.assertEqual(
            json.loads(response.content)["thematiques"],
            ["numerique--acceder-a-du-materiel"],
        )
