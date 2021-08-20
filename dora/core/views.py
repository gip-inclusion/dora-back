from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils.text import get_valid_filename
from rest_framework import permissions
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from dora.structures.models import Structure


@api_view(["POST"])
@parser_classes([FileUploadParser])
@permission_classes([permissions.AllowAny])
def upload(request, filename, structure_slug):
    # TODO: check that I have permission to upload to this service
    structure = get_object_or_404(Structure.objects.all(), slug=structure_slug)
    file_obj = request.data["file"]
    clean_filename = f"{structure.id}/{get_valid_filename(filename)}"
    result = default_storage.save(clean_filename, file_obj)
    return Response({"key": result}, status=201)


def trigger_error(request):
    division_by_zero = 1 / 0
    print(division_by_zero)
