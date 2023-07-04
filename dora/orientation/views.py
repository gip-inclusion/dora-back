from django.conf import settings
from django.template.loader import render_to_string
from mjml import mjml2html
from rest_framework import mixins, permissions, viewsets

from dora.structures.models import Structure

from ..core.emails import send_mail
from .models import Orientation
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

    def get_queryset(self):
        return Orientation.objects.all()

    def perform_create(self, serializer):
        serializer.is_valid()

        orientation = serializer.save(prescriber=self.request.user)
        send_orientation_email(orientation)


def send_orientation_email(orientation):
    beneficiary_contact_info = f"{orientation.beneficiary_email}"  # TODO
    mjml_string = render_to_string(
        "structure.mjml",
        {
            "data": orientation,
            "homepage_url": settings.FRONTEND_URL,
            "beneficiary_contact_info": beneficiary_contact_info,
        },
    )
    # print(mjml_string)
    print([x for x in orientation.__dict__.items() if not x[0].startswith("_")])
    body = mjml2html(mjml_string)

    send_mail(
        "[DORA] Nouvelle demande d'orientation reçue",
        settings.SERVER_EMAIL,
        body,
        tags=["orientation"],
        reply_to=None,
    )
