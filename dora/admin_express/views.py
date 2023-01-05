from django.contrib.gis.geos import Point
from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import exceptions, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from dora.admin_express.utils import normalize_string_for_search

from .models import EPCI, AdminDivisionType, City, Department, Region


@api_view()
@permission_classes([permissions.AllowAny])
def search(request):
    class AdminDivisionSerializer(serializers.Serializer):
        code = serializers.CharField()
        name = serializers.CharField()
        similarity = serializers.FloatField()

    type = request.GET.get("type", "")
    q = request.GET.get("q", "")
    if not type or not q:
        raise exceptions.ValidationError("type and q are required")
    norm_q = normalize_string_for_search(q)

    Model = None
    sort_fields = ["-similarity"]
    if type == AdminDivisionType.CITY:
        Model = City
        sort_fields = ["-similarity", "-population"]
    elif type == AdminDivisionType.EPCI:
        Model = EPCI
    elif type == AdminDivisionType.DEPARTMENT:
        Model = Department
    elif type == AdminDivisionType.REGION:
        Model = Region
    else:
        raise exceptions.ValidationError(
            f"Invalid type, expected one of {AdminDivisionType.CITY}, {AdminDivisionType.EPCI}, {AdminDivisionType.DEPARTMENT}, {AdminDivisionType.REGION}"
        )

    qs = (
        Model.objects.defer("geom")
        .annotate(similarity=TrigramSimilarity("normalized_name", norm_q))
        .filter(similarity__gt=0.1 if len(q) > 3 else 0)
        .order_by(*sort_fields)[:10]
    )

    return Response(AdminDivisionSerializer(qs.all(), many=True).data)


@api_view()
@permission_classes([permissions.AllowAny])
def reverse_search(request):
    class AdminDivisionSerializer(serializers.Serializer):
        code = serializers.CharField()
        name = serializers.CharField()

    type = request.GET.get("type")
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")
    if not type or not lat or not lon:
        raise exceptions.ValidationError("type, lat and lon are required")
    point = Point(float(lon), float(lat), srid=4326)

    Model = None
    if type == AdminDivisionType.CITY:
        Model = City
    elif type == AdminDivisionType.EPCI:
        Model = EPCI
    elif type == AdminDivisionType.DEPARTMENT:
        Model = Department
    elif type == AdminDivisionType.REGION:
        Model = Region
    else:
        raise exceptions.ValidationError(
            f"Invalid type, expected one of {AdminDivisionType.CITY}, {AdminDivisionType.EPCI}, {AdminDivisionType.DEPARTMENT}, {AdminDivisionType.REGION}"
        )

    result = Model.objects.filter(geom__covers=point).first()
    if result is not None:
        return Response(AdminDivisionSerializer(result).data)
    raise NotFound


@api_view()
@permission_classes([permissions.AllowAny])
def get_city_label(request, insee_code):
    city = City.objects.get_from_code(insee_code)
    if city:
        return Response(city.name)
    raise NotFound
