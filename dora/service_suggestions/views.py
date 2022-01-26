from rest_framework import mixins, permissions, viewsets

from dora.core.notify import send_mattermost_notification
from dora.service_suggestions.models import ServiceSuggestion
from dora.sirene.models import Establishment
from dora.sirene.serializers import EstablishmentSerializer
from dora.structures.models import Structure

from .serializers import ServiceSuggestionSerializer


class ServiceSuggestionPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method == "POST"

    def has_object_permission(self, request, view, obj):
        return False


class ServiceSuggestionViewSet(
    mixins.CreateModelMixin,
    # mixins.RetrieveModelMixin,
    # mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [ServiceSuggestionPermission]
    serializer_class = ServiceSuggestionSerializer

    def get_queryset(self):
        return ServiceSuggestion.objects.all()

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        suggestion = serializer.save(
            creator=user,
        )

        establishment = Establishment.objects.get(siret=suggestion.siret)
        establishment_data = EstablishmentSerializer(establishment).data
        structure_exists = Structure.objects.filter(siret=suggestion.siret).exists()

        send_mattermost_notification(
            f":bulb: Nouvelle suggestion de service “{suggestion.name}” pour la {'**nouvelle** ' if structure_exists else ''}structure {'existante' if not structure_exists else ''}: **{establishment_data['name']} ({establishment_data['city_code']})**"
        )
