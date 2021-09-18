from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.text import get_valid_filename
from rest_framework import permissions
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from dora.structures.models import Structure, StructureMember
from dora.users.models import User

from .serializers import ServiceAndUserSerializer


@api_view(["POST"])
@parser_classes([FileUploadParser])
@permission_classes([permissions.AllowAny])
def upload(request, filename, structure_slug):
    # TODO: check that I have permission to upload to this service
    structure = get_object_or_404(Structure.objects.all(), slug=structure_slug)
    file_obj = request.data["file"]
    clean_filename = (
        f"{settings.ENVIRONMENT}/{structure.id}/{get_valid_filename(filename)}"
    )
    result = default_storage.save(clean_filename, file_obj)
    return Response({"key": result}, status=201)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@transaction.atomic
def register_service_and_user(request):
    serializer = ServiceAndUserSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data

    # Create User
    user = User.objects.create_user(data["email"], data["password"], name=data["name"])

    # Create Structure
    establishment = data["establishment"]
    is_new_structure = False
    try:
        structure = Structure.objects.get(siret=establishment.siret)
    except Structure.DoesNotExist:
        structure = Structure.objects.create_from_establishment(establishment)
        is_new_structure = True
        structure.creator = user
        structure.last_editor = user
        structure.save()

    # Link them
    StructureMember.objects.create(
        user=user, structure=structure, is_admin=is_new_structure
    )

    # TODO Send validation link email
    return Response(status=201)


def trigger_error(request):
    division_by_zero = 1 / 0
    print(division_by_zero)
