from django.core.files.storage import default_storage
from rest_framework import permissions
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response


@api_view()
@permission_classes([permissions.AllowAny])
def hello_world(request):
    return Response({"message": "Hello from Django!"})


@api_view(["POST"])
@parser_classes([FileUploadParser])
@permission_classes([permissions.AllowAny])
def upload(request, filename):
    file_obj = request.data["file"]
    result = default_storage.save(filename, file_obj)
    return Response({"key": result}, status=201)


def trigger_error(request):
    division_by_zero = 1 / 0
    print(division_by_zero)
