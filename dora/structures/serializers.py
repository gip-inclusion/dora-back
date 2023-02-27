from django.db.models import Count, Q
from rest_framework import exceptions, serializers

from dora.services.enums import ServiceStatus
from dora.services.models import Service, ServiceModel
from dora.services.serializers import ServiceListSerializer
from dora.structures.emails import send_invitation_email
from dora.users.models import User

from .models import (
    Structure,
    StructureMember,
    StructureNationalLabel,
    StructurePutativeMember,
    StructureTypology,
)


class StructureSerializer(serializers.ModelSerializer):
    typology = serializers.SlugRelatedField(
        slug_field="value", queryset=StructureTypology.objects.all()
    )
    typology_display = serializers.SerializerMethodField()
    parent = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    can_write = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_pending_member = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    branches = serializers.SerializerMethodField()

    has_admin = serializers.SerializerMethodField()

    num_services = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    archived_services = serializers.SerializerMethodField()

    num_models = serializers.SerializerMethodField()
    models = serializers.SerializerMethodField()

    national_labels = serializers.SlugRelatedField(
        slug_field="value",
        queryset=StructureNationalLabel.objects.all(),
        many=True,
        required=False,
    )

    source = serializers.SerializerMethodField()

    city = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = [
            "accesslibre_url",
            "address1",
            "address2",
            "ape",
            "archived_services",
            "branches",
            "can_write",
            "city",
            "city_code",
            "code_safir_pe",
            "creation_date",
            "department",
            "email",
            "full_desc",
            "has_admin",
            "has_been_edited",
            "quick_start_done",
            "is_admin",
            "is_member",
            "is_pending_member",
            "latitude",
            "longitude",
            "models",
            "modification_date",
            "name",
            "national_labels",
            "num_models",
            "num_services",
            "opening_hours",
            "opening_hours_details",
            "other_labels",
            "parent",
            "phone",
            "postal_code",
            "services",
            "short_desc",
            "siret",
            "slug",
            "source",
            "typology",
            "typology_display",
            "url",
        ]
        lookup_field = "slug"
        read_only_fields = ["has_been_edited"]

    def get_has_admin(self, obj):
        return obj.membership.filter(is_admin=True).exists()

    def get_can_write(self, obj):
        # TODO: DEPRECATED
        user = self.context.get("request").user
        return obj.can_write(user)

    def get_is_member(self, obj):
        user = self.context.get("request").user
        return obj.is_member(user)

    def get_is_pending_member(self, obj):
        user = self.context.get("request").user
        return obj.is_pending_member(user)

    def get_is_admin(self, obj):
        user = self.context.get("request").user
        return obj.is_admin(user)

    def get_typology_display(self, obj):
        return obj.typology.label if obj.typology else ""

    def get_num_services(self, structure):
        return structure.get_num_visible_services(self.context["request"].user)

    def get_services(self, obj):
        class StructureServicesSerializer(ServiceListSerializer):
            structure = serializers.SlugRelatedField(
                queryset=Structure.objects.all(),
                slug_field="slug",
                required=False,
            )

            class Meta:
                model = Service
                fields = [
                    "address1",
                    "address2",
                    "categories_display",
                    "category",
                    "category_display",
                    "city",
                    "city",
                    "city_code",
                    "coach_orientation_modes",
                    "contact_email",
                    "contact_name",
                    "contact_phone",
                    "department",
                    "diffusion_zone_details_display",
                    "diffusion_zone_type",
                    "diffusion_zone_type_display",
                    "is_available",
                    "is_cumulative",
                    "location_kinds",
                    "location_kinds_display",
                    "model",
                    "model_changed",
                    "modification_date",
                    "name",
                    "postal_code",
                    "postal_code",
                    "remote_url",
                    "short_desc",
                    "slug",
                    "status",
                    "structure",
                    "use_inclusion_numerique_scheme",
                ]

        user = self.context.get("request").user
        qs = obj.services.published()
        if user.is_authenticated and (user.is_staff or obj.is_member(user)):
            qs = obj.services.active()

        qs = qs.filter(is_model=False)
        return StructureServicesSerializer(
            qs.prefetch_related(
                "categories",
            ),
            many=True,
        ).data

    def get_archived_services(self, obj):
        class StructureServicesSerializer(ServiceListSerializer):
            structure = serializers.SlugRelatedField(
                queryset=Structure.objects.all(),
                slug_field="slug",
                required=False,
            )

            class Meta:
                model = Service
                fields = [
                    "categories_display",
                    "category",
                    "category_display",
                    "city",
                    "department",
                    "diffusion_zone_details_display",
                    "diffusion_zone_type",
                    "diffusion_zone_type_display",
                    "is_available",
                    "model",
                    "model_changed",
                    "modification_date",
                    "name",
                    "postal_code",
                    "short_desc",
                    "slug",
                    "status",
                    "structure",
                    "use_inclusion_numerique_scheme",
                ]

        user = self.context.get("request").user
        qs = obj.services.none()
        if user.is_authenticated and (user.is_staff or obj.is_member(user)):
            qs = obj.services.archived()

        qs = qs.filter(is_model=False)
        return StructureServicesSerializer(
            qs.prefetch_related(
                "categories",
            ),
            many=True,
        ).data

    def get_num_models(self, structure):
        return structure.get_num_visible_models(self.context["request"].user)

    def get_models(self, structure):
        class StructureModelsSerializer(ServiceListSerializer):
            structure = serializers.SlugRelatedField(
                queryset=Structure.objects.all(),
                slug_field="slug",
                required=False,
            )

            num_services = serializers.SerializerMethodField()

            class Meta:
                model = ServiceModel
                fields = [
                    "categories_display",
                    "department",
                    "modification_date",
                    "name",
                    "num_services",
                    "short_desc",
                    "slug",
                    "structure",
                ]

            def get_num_services(self, obj):
                return obj.copies.exclude(status=ServiceStatus.ARCHIVED).count()

        qs = ServiceModel.objects.filter(structure=structure)
        return StructureModelsSerializer(
            qs.prefetch_related(
                "categories",
            ),
            many=True,
        ).data

    def get_branches(self, obj):
        class StructureListSerializerWithCount(StructureListSerializer):
            num_services = serializers.IntegerField()

            class Meta:
                model = Structure
                fields = [
                    "department",
                    "modification_date",
                    "name",
                    "num_services",
                    "slug",
                    "typology_display",
                ]
                lookup_field = "slug"

        user = self.context.get("request").user
        if user.is_authenticated and user.is_staff:
            branches = obj.branches.annotate(
                num_services=Count(
                    "services",
                    filter=Q(
                        services__status__in=(
                            ServiceStatus.DRAFT,
                            ServiceStatus.SUGGESTION,
                            ServiceStatus.PUBLISHED,
                        )
                    ),
                )
            )
        else:
            branches_member_of = (
                obj.branches.filter(membership__user=user)
                if user.is_authenticated
                else Structure.objects.none()
            )
            branches_other = obj.branches.exclude(pk__in=branches_member_of)
            branches = [
                *list(
                    branches_member_of.annotate(
                        num_services=Count(
                            "services",
                            filter=Q(
                                services__status__in=(
                                    ServiceStatus.DRAFT,
                                    ServiceStatus.SUGGESTION,
                                    ServiceStatus.PUBLISHED,
                                )
                            ),
                        )
                    )
                ),
                *list(
                    branches_other.annotate(
                        num_services=Count(
                            "services",
                            filter=Q(services__status=ServiceStatus.PUBLISHED),
                        )
                    )
                ),
            ]
        return StructureListSerializerWithCount(branches, many=True).data

    def get_source(self, obj):
        return (
            {"value": obj.source.value, "label": obj.source.label}
            if obj.source
            else None
        )

    def get_city(self, obj):
        return obj.get_clean_city_name()


class StructureListSerializer(StructureSerializer):
    class Meta:
        model = Structure
        fields = [
            "department",
            "modification_date",
            "name",
            "parent",
            "siret",
            "slug",
            "typology_display",
        ]
        lookup_field = "slug"


class SiretClaimedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Structure
        fields = ["siret", "slug"]
        lookup_field = "siret"


class UserSerializer(serializers.ModelSerializer):
    # We want to suppress the unique constraint validation here
    # as we might get passed an existing user email on creation
    email = serializers.EmailField(label="Email address", max_length=255, validators=[])
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "full_name", "email"]


class StructureMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = StructureMember
        fields = [
            "id",
            "is_admin",
            "user",
        ]
        validators = []

    def validate(self, data):
        structure_slug = self.context["request"].query_params.get("structure")
        if structure_slug:
            try:
                structure = Structure.objects.get(slug=structure_slug)
            except Structure.DoesNotExist:
                raise exceptions.NotFound
            data["structure"] = structure
        return data

    def update(self, instance, validated_data):
        # For now, we don't want the user to be editable this way
        # user_data = validated_data.pop("user") if "user" in validated_data else {}
        # user = instance.user
        # for attr, value in user_data.items():
        #     setattr(user, attr, value)
        # user.save()

        if "user" in validated_data:
            validated_data.pop("user")
        if instance.is_admin and validated_data.get("is_admin") is False:
            request_user = self.context["request"].user
            if not request_user.is_staff:
                # Only remove admin status if there's at least another one
                num_admins = StructureMember.objects.filter(
                    structure=instance.structure, is_admin=True
                ).count()
                if num_admins == 1:
                    raise exceptions.PermissionDenied
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class StructurePutativeMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = StructurePutativeMember
        fields = [
            "id",
            "invited_by_admin",
            "is_admin",
            "user",
        ]
        validators = []

    def validate(self, data):
        structure_slug = self.context["request"].query_params.get("structure")
        if structure_slug:
            try:
                structure = Structure.objects.get(slug=structure_slug)
            except Structure.DoesNotExist:
                raise exceptions.NotFound
            data["structure"] = structure
        return data

    def create(self, validated_data):
        request_user = self.context["request"].user
        user_data = validated_data.pop("user")
        try:
            user = User.objects.get(email=user_data["email"])
        except User.DoesNotExist:
            # TODO: use create_user instead
            user = User.objects.create(**user_data)
            user.set_unusable_password()
            user.save()
        try:
            StructurePutativeMember.objects.get(
                user=user, structure=validated_data["structure"]
            )
            raise exceptions.PermissionDenied
        except StructurePutativeMember.DoesNotExist:
            pass
        member = StructurePutativeMember.objects.create(
            user=user,
            **validated_data,
            invited_by_admin=True,
        )
        # Send invitation email
        send_invitation_email(
            member,
            request_user.get_full_name(),
        )
        return member
