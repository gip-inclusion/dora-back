from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from dora.admin_express.utils import main_insee_code_to_arrdts
from dora.structures.models import Structure

from .models import Establishment
from .serializers import EstablishmentSerializer


@api_view()
@permission_classes([permissions.AllowAny])
def search_sirene(request, citycode):
    q = request.query_params.get("q", "")
    if not q:
        return Response("need q")

    # La base SIRENE contient les code insee par arrondissement
    # mais on veut faire une recherche sur la ville entière
    citycodes = main_insee_code_to_arrdts(citycode)

    results = (
        Establishment.objects.filter(city_code__in=citycodes)
        .annotate(similarity=TrigramSimilarity("full_search_text", q))
        .order_by("-similarity")
    )

    # Exclut les structures marquées comme obsolètes
    results = results.exclude(
        siret__in=Structure.objects.filter(is_obsolete=True).values_list(
            "siret", flat=True
        )
    )

    return Response(
        EstablishmentSerializer(
            results[:10], many=True, context={"request": request}
        ).data
    )


@api_view()
@permission_classes([permissions.AllowAny])
def search_all_sirene(request):
    q = request.query_params.get("q", "")
    if not q:
        return Response("need q")

    results = Establishment.objects.annotate(
        similarity=TrigramSimilarity("full_search_text", q)
    ).order_by("-similarity")

    return Response(
        EstablishmentSerializer(
            results[:10], many=True, context={"request": request}
        ).data
    )


@api_view()
@permission_classes([permissions.AllowAny])
def search_siret(request):
    siret = request.query_params.get("siret", "")
    if not siret:
        return Response("need siret")

    try:
        establishment = Establishment.objects.get(siret=siret)
    except Establishment.DoesNotExist:
        raise NotFound

    return Response(
        EstablishmentSerializer(establishment, context={"request": request}).data
    )


@api_view()
@permission_classes([permissions.AllowAny])
def search_safir(request):
    safir = request.query_params.get("safir", "")
    if not safir:
        return Response("`safir` requis")
    try:
        pe_structure = Structure.objects.get(code_safir_pe=safir)
    except Structure.DoesNotExist:
        raise NotFound
    return Response(
        {
            "address1": pe_structure.address1,
            "address2": pe_structure.address2,
            "city": pe_structure.city,
            "name": pe_structure.name,
            "postal_code": pe_structure.postal_code,
            "siret": pe_structure.siret
            or (pe_structure.parent.siret if pe_structure.parent else ""),
            "slug": pe_structure.slug,
        }
    )
