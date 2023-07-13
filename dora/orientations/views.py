from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..core.utils import TRUTHY_VALUES
from .emails import (
    send_message_to_beneficiary,
    send_message_to_prescriber,
    send_orientation_accepted_emails,
    send_orientation_created_emails,
    send_orientation_rejected_emails,
)
from .models import Orientation, OrientationStatus, RejectionReason
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
        prescriberMessage = self.request.data.get("message")
        beneficiaryMessage = self.request.data.get("beneficiary_message")
        orientation.processing_date = timezone.now()
        orientation.status = OrientationStatus.ACCEPTED
        orientation.save()
        send_orientation_accepted_emails(
            orientation, prescriberMessage, beneficiaryMessage
        )
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
        permission_classes=[permissions.AllowAny],
    )
    def reject(self, request, query_id=None):
        orientation = self.get_object()
        message = self.request.data.get("message", "")
        reasons = self.request.data.get("reasons", [])
        orientation.processing_date = timezone.now()
        orientation.status = OrientationStatus.REJECTED
        orientation.save()
        orientation.rejection_reasons.set(
            RejectionReason.objects.filter(value__in=reasons)
        )
        send_orientation_rejected_emails(orientation, message)
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="contact/beneficiary",
        permission_classes=[permissions.AllowAny],
    )
    def contact_beneficiary(self, request, query_id=None):
        # TODO: logguer le fait qu'un message a été envoyé, et sa date

        orientation = self.get_object()
        message = self.request.data.get("message")
        cc_prescriber = self.request.data.get("cc_prescriber") in TRUTHY_VALUES
        cc_referent = self.request.data.get("cc_referent") in TRUTHY_VALUES
        send_message_to_beneficiary(orientation, message, cc_prescriber, cc_referent)
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="contact/prescriber",
        permission_classes=[permissions.AllowAny],
    )
    def contact_prescriber(self, request, query_id=None):
        # TODO: logguer le fait qu'un message a été envoyé, et sa date
        orientation = self.get_object()
        message = self.request.data.get("message")
        cc_beneficiary = self.request.data.get("cc_beneficiary") in TRUTHY_VALUES
        cc_referent = self.request.data.get("cc_referent") in TRUTHY_VALUES
        send_message_to_prescriber(orientation, message, cc_beneficiary, cc_referent)
        return Response(status=204)
