from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Establishment
from .serializers import EstablishmentSerializer

# prepare DB https://stackoverflow.com/questions/47230566/using-unaccent-with-searchvector-and-searchquery-in-django
# or rather just unaccent the query string?
# Add a search vector field for faster search


@api_view()
@permission_classes([permissions.AllowAny])
def search_sirene(request, citycode):
    q = request.query_params.get("q", "")
    if not q:
        return Response("need q")

    results = (
        Establishment.objects.filter(code_commune=citycode)
        .annotate(similarity=TrigramSimilarity("full_search_text", q))
        .order_by("-similarity")
    )

    return Response(EstablishmentSerializer(results[:10], many=True).data)


@api_view()
@permission_classes([permissions.AllowAny])
def search_all_sirene(request):
    q = request.query_params.get("q", "")
    if not q:
        return Response("need q")

    results = Establishment.objects.annotate(
        similarity=TrigramSimilarity("full_search_text", q)
    ).order_by("-similarity")

    return Response(EstablishmentSerializer(results[:10], many=True).data)
