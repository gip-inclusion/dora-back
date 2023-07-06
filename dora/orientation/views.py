from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from mjml import mjml2html
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from dora.structures.models import Structure

from ..core.emails import send_mail
from .models import Orientation, OrientationStatus
from .serializers import OrientationSerializer


class OrientationPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, structure: Structure):
        return True


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

    @action(
        detail=True,
        methods=["post"],
        url_path="validate",
        permission_classes=[permissions.AllowAny],
    )
    def validate(self, request):
        orientation = self.get_object()
        # message = self.request.data.get("message")
        orientation.processing_date = timezone.now()
        orientation.status = OrientationStatus.ACCEPTED
        orientation.save()
        # todo: send mails
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
        permission_classes=[permissions.AllowAny],
    )
    def reject(self, request):
        orientation = self.get_object()
        # message = self.request.data.get("message")
        orientation.processing_date = timezone.now()
        orientation.status = OrientationStatus.REJECTED
        orientation.save()
        # todo: send mails
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="contact/beneficiary",
        permission_classes=[permissions.AllowAny],
    )
    def contact_beneficiary(self, request):
        # orientation = self.get_object()
        # message = self.request.data.get("message")
        return Response(status=204)

    @action(
        detail=True,
        methods=["post"],
        url_path="contact/prescriber",
        permission_classes=[permissions.AllowAny],
    )
    def contact_prescriber(self, request):
        # orientation = self.get_object()
        # message = self.request.data.get("message")
        return Response(status=204)

    def perform_create(self, serializer):
        serializer.is_valid()

        orientation = serializer.save(prescriber=self.request.user)
        send_orientation_emails(orientation)


def send_orientation_emails(orientation):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "magic_link": orientation.get_magic_link(),
    }
    # Structure porteuse
    send_mail(
        "[DORA] Nouvelle demande d'orientation reçue",
        orientation.service.contact_email,
        mjml2html(render_to_string("orientation-created-structure.mjml", context)),
        from_email=(
            f"{orientation.prescriber.get_full_name()} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.referent_email, orientation.prescriber.email],
        attachments=orientation.beneficiary_attachments,
    )
    # Prescripteur
    send_mail(
        "[DORA] Votre demande a bien été transmise !",
        orientation.prescriber.email,
        mjml2html(render_to_string("orientation-created-prescriber.mjml", context)),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email, orientation.referent_email],
    )
    # Référent
    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        send_mail(
            "[DORA] Notification d'une demande d'orientation",
            orientation.referent_email,
            mjml2html(render_to_string("orientation-created-referent.mjml", context)),
            from_email=(
                f"{orientation.prescriber.get_full_name()} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.service.contact_email, orientation.prescriber.email],
        )
    # Bénéficiaire
    if orientation.beneficiary_email:
        send_mail(
            "[DORA] Une orientation a été effectuée en votre nom",
            orientation.beneficiary_email,
            mjml2html(
                render_to_string("orientation-created-beneficiary.mjml", context)
            ),
            tags=["orientation"],
            reply_to=[orientation.referent_email, orientation.prescriber.email],
        )
