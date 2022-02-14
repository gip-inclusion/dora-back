from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import exceptions, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.admin_express.utils import normalize_string_for_search

from .models import EPCI, AdminDivisionType, City, Department, Region


class AdminDivisionSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    similarity = serializers.FloatField()


@api_view()
@permission_classes([permissions.AllowAny])
def search(request):
    MIN_LENGTH = 1
    type = request.GET.get("type", "")
    q = request.GET.get("q", "")
    if not type or not q:
        raise exceptions.ValidationError("type and q are required")
    if len(q) < MIN_LENGTH:
        raise exceptions.ValidationError(
            f"q should be at least {MIN_LENGTH} characters long"
        )
    norm_q = normalize_string_for_search(q)
    qs = None

    sort_fields = ["-similarity"]
    if type == AdminDivisionType.CITY:
        # On accelère la recherche sur les villes en ancrant le premier caractère
        qs = City.objects.defer("geom").filter(normalized_name__startswith=norm_q[0])
        sort_fields = ["-similarity", "-population"]
    elif type == AdminDivisionType.EPCI:
        qs = EPCI.objects.defer("geom").all()
    elif type == AdminDivisionType.DEPARTMENT:
        qs = Department.objects.defer("geom").all()
    elif type == AdminDivisionType.REGION:
        qs = Region.objects.defer("geom").all()

    if qs:
        qs = (
            qs.annotate(similarity=TrigramSimilarity("normalized_name", norm_q))
            .filter(similarity__gt=0.2 if len(q) > 3 else 0)
            .order_by(*sort_fields)[:10]
        )

        return Response(AdminDivisionSerializer(qs.values(), many=True).data)
    else:
        return Response([])
