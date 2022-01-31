import uuid

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import models, transaction
from rest_framework import serializers

from dora.core.utils import code_insee_to_code_dept
from dora.core.validators import validate_siret
from dora.services.models import Service
from dora.sirene.models import Establishment
from dora.sirene.serializers import EstablishmentSerializer
from dora.structures.models import Structure, StructureSource


class ServiceSuggestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    siret = models.CharField(
        verbose_name="Siret", max_length=14, validators=[validate_siret], db_index=True
    )
    name = models.CharField(verbose_name="Nom de l’offre", max_length=140)
    creation_date = models.DateTimeField(auto_now_add=True)
    contents = models.JSONField(default=dict)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )

    def get_structure_info(self):
        try:
            structure = Structure.objects.get(siret=self.siret)
            return {
                "name": structure.name,
                "department": structure.department,
                "new": False,
            }
        except Structure.DoesNotExist:
            try:
                data = EstablishmentSerializer(
                    Establishment.objects.get(siret=self.siret)
                ).data
                dept = code_insee_to_code_dept(data["city_code"])
                return {"name": data["name"], "department": dept, "new": True}
            except Establishment.DoesNotExist:
                raise serializers.ValidationError("SIRET inconnu", code="wrong_siret")

    def convert_to_service(self):
        try:
            structure = Structure.objects.get(siret=self.siret)
        except Structure.DoesNotExist:
            try:
                establishment = Establishment.objects.get(siret=self.siret)
                structure = Structure.objects.create_from_establishment(establishment)
                structure.creator = self.creator
                structure.last_editor = self.creator
                structure.source = StructureSource.COLLAB
                structure.save()
            except Establishment.DoesNotExist:
                raise serializers.ValidationError("SIRET inconnu", code="wrong_siret")

        access_conditions = self.contents.pop("access_conditions", [])
        concerned_public = self.contents.pop("concerned_public", [])
        requirements = self.contents.pop("requirements", [])
        credentials = self.contents.pop("credentials", [])

        lon = self.contents.pop("longitude", None)
        lat = self.contents.pop("latitude", None)
        if lon and lat:
            geom = Point(lon, lat, srid=4326)
        else:
            geom = None
        with transaction.atomic(durable=True):
            service = Service.objects.create(
                name=self.name,
                structure=structure,
                geom=geom,
                creator=self.creator,
                last_editor=self.creator,
                is_draft=True,
                is_suggestion=True,
                **self.contents,
            )
            service.access_conditions.set(access_conditions)
            service.concerned_public.set(concerned_public)
            service.requirements.set(requirements)
            service.credentials.set(credentials)

            self.delete()
        return service
