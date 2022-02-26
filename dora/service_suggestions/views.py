from django.conf import settings
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from dora.core.notify import send_mattermost_notification
from dora.service_suggestions.models import ServiceSuggestion
from dora.sirene.models import Establishment
from dora.sirene.serializers import EstablishmentSerializer
from dora.structures.models import Structure

from .serializers import ServiceSuggestionSerializer


class ServiceSuggestionPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # Anybody can create a new contribution
        if request.method == "POST":
            return True
        else:
            # Only bizdevs or staff can do anything else
            return request.user.is_authenticated and (
                request.user.is_bizdev or request.user.is_staff
            )

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and (
            request.user.is_bizdev or request.user.is_staff
        )


class ServiceSuggestionValidationPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_bizdev or request.user.is_staff
        )


class ServiceSuggestionViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [ServiceSuggestionPermission]
    serializer_class = ServiceSuggestionSerializer

    def get_queryset(self):
        return ServiceSuggestion.objects.all().order_by("-creation_date")

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        suggestion = serializer.save(
            creator=user,
        )

        establishment = Establishment.objects.get(siret=suggestion.siret)
        establishment_data = EstablishmentSerializer(establishment).data
        structure_exists = Structure.objects.filter(siret=suggestion.siret).exists()

        send_mattermost_notification(
            f":bulb: Nouvelle suggestion de service “{suggestion.name}” pour la {'**nouvelle** ' if structure_exists else ''}structure {'existante' if not structure_exists else ''}: **{establishment_data['name']} ({establishment_data['city_code']})**\n{settings.FRONTEND_URL}/tableau-de-bord/service-suggestions"
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="validate",
        permission_classes=[ServiceSuggestionValidationPermission],
    )
    def validate_suggestion(self, request, pk):
        suggestion = self.get_object()
        suggestion.convert_to_service()
        return Response(status=201)
