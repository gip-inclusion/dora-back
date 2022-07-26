import uuid

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import models, transaction
from dora.service_suggestions.emails import (
    send_suggestion_validated_existing_structure_email,
    send_suggestion_validated_new_structure_email,
)
from rest_framework import serializers

from dora.core.utils import code_insee_to_code_dept
from dora.core.validators import validate_siret
from dora.services.enums import ServiceStatus
from dora.services.models import (
    LocationKind,
    Service,
    ServiceCategory,
    ServiceKind,
    ServiceSubCategory,
)
from dora.sirene.models import Establishment
from dora.sirene.serializers import EstablishmentSerializer
from dora.structures.models import Structure, StructureMember, StructureSource


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

    class Meta:
        verbose_name = "Contribution de service"
        verbose_name_plural = "Contributions de service"

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

    def convert_to_service(self, send_notification_mail=False):
        def values_to_objects(Model, values):
            return [Model.objects.get(value=v) for v in values]

        is_new_structure = False
        try:
            structure = Structure.objects.get(siret=self.siret)
        except Structure.DoesNotExist:
            is_new_structure = True

            try:
                establishment = Establishment.objects.get(siret=self.siret)
                structure = Structure.objects.create_from_establishment(establishment)
                structure.creator = self.creator
                structure.last_editor = self.creator
                structure.source = StructureSource.objects.get(
                    value="suggestion-collaborative"
                )
                structure.save()
            except Establishment.DoesNotExist:
                raise serializers.ValidationError("SIRET inconnu", code="wrong_siret")

        access_conditions = self.contents.pop("access_conditions", [])
        concerned_public = self.contents.pop("concerned_public", [])
        requirements = self.contents.pop("requirements", [])
        credentials = self.contents.pop("credentials", [])
        categories = self.contents.pop("categories", [])
        subcategories = self.contents.pop("subcategories", [])
        kinds = self.contents.pop("kinds", [])
        location_kinds = self.contents.pop("location_kinds", [])

        # rétrocompatibilité: les anciennes suggestion avaient uniquement
        # un champ "category" au lieu du champ "categories" multiple
        category = self.contents.pop("category", "")
        if category:
            categories = [category]

        lon = self.contents.pop("longitude", None)
        lat = self.contents.pop("latitude", None)
        contact_phone = "".join(
            [s for s in self.contents.pop("contact_phone", "") if s.isdigit()]
        )[:10]
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
                status=ServiceStatus.SUGGESTION,
                contact_phone=contact_phone,
                **self.contents,
            )
            service.access_conditions.set(access_conditions)
            service.concerned_public.set(concerned_public)
            service.requirements.set(requirements)
            service.credentials.set(credentials)

            service.categories.set(values_to_objects(ServiceCategory, categories))
            service.subcategories.set(
                values_to_objects(ServiceSubCategory, subcategories)
            )
            service.kinds.set(values_to_objects(ServiceKind, kinds))
            service.location_kinds.set(values_to_objects(LocationKind, location_kinds))

            self.delete()

        emails_contacted = set()
        if send_notification_mail:
            contact_email = self.contents.get("contact_email", None) or None
            if is_new_structure:
                # Pour les nouvelles structures, on envoie un mail à la personne indiquée
                # dans le formulaire (si présent)
                if contact_email is not None:
                    send_suggestion_validated_new_structure_email(
                        contact_email, structure
                    )
                    emails_contacted.add(contact_email)
            else:
                # Pour une structure existante et dont l'administrateur est connu, on envoie un e-mail à ce dernier
                # - et potentiellement au contact_email si différent de l'administrateur
                structure_admins = StructureMember.objects.filter(
                    structure=structure, is_admin=True
                )
                for admin in structure_admins:
                    emails_contacted.add(admin.user.email)

                if contact_email is not None:
                    emails_contacted.add(contact_email)

                if len(emails_contacted):
                    send_suggestion_validated_existing_structure_email(
                        list(emails_contacted), structure, service
                    )

        return service, list(emails_contacted)
