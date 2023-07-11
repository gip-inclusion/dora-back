from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .emails import (
    send_message_to_beneficiary,
    send_message_to_prescriber,
    send_orientation_accepted_emails,
    send_orientation_created_emails,
    send_orientation_rejected_emails,
)
from .models import Orientation, OrientationStatus
from .serializers import OrientationSerializer


class OrientationPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "DELETE":
            return False
        if request.method == "POST":
            return request.user.is_authenticated
        return True

    def has_object_permission(self, request, view, orientation):
        return request.method in ["GET", "POST"]


class OrientationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrientationSerializer
    permission_classes = [OrientationPermission]
    lookup_field = "query_id"

    def get_queryset(self):
        return Orientation.objects.all()

    def perform_create(self, serializer):
        serializer.is_valid()
        orientation = serializer.save(prescriber=self.request.user)
        send_orientation_created_emails(orientation)

    @action(
        detail=True,
        methods=["post"],
        url_path="validate",
        permission_classes=[permissions.AllowAny],
    )
    def validate(self, request, query_id=None):
        orientation = self.get_object()
        # message = self.request.data.get("message")
        orientation.processing_date = timezone.now()
        orientation.status = OrientationStatus.ACCEPTED
        orientation.save()
        send_orientation_accepted_emails(orientation)
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
        permission_classes=[permissions.AllowAny],
    )
    def reject(self, request, query_id=None):
        orientation = self.get_object()
        # message = self.request.data.get("message")
        orientation.processing_date = timezone.now()
        orientation.status = OrientationStatus.REJECTED
        orientation.save()
        send_orientation_rejected_emails(orientation)
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="contact/beneficiary",
        permission_classes=[permissions.AllowAny],
    )
    def contact_beneficiary(self, request, query_id=None):
        orientation = self.get_object()
        message = self.request.data.get("message")
        send_message_to_beneficiary(orientation, message)
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="contact/prescriber",
        permission_classes=[permissions.AllowAny],
    )
    def contact_prescriber(self, request, query_id=None):
        orientation = self.get_object()
        message = self.request.data.get("message")
        send_message_to_prescriber(orientation, message)
        return Response(status=204)
