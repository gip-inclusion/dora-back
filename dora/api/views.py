from rest_framework import permissions, viewsets

from dora.services.models import Service
from dora.structures.models import Structure

from .serializers import ServiceSerializer, StructureSerializer


class StructureViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Structure.objects.all()
    serializer_class = StructureSerializer
    permission_classes = [permissions.AllowAny]


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Service.objects.filter(is_draft=False, is_suggestion=False)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
