import random
from datetime import date
from typing import Optional

import requests
from _operator import itemgetter
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import IntegerField, Q, Value
from django.shortcuts import get_object_or_404
from django.utils import timezone

import dora.services.models as models
from dora import data_inclusion
from dora.admin_express.models import City
from dora.admin_express.utils import arrdt_to_main_insee_code

from .serializers import SearchResultSerializer
from .utils import filter_services_by_city_code


def _filter_and_annotate_dora_services(services, location):
    # 1) services ayant un lieu de déroulement, à moins de 100km
    services_on_site = (
        services.filter(location_kinds__value="en-presentiel")
        .annotate(distance=Distance("geom", location))
        .filter(distance__lte=D(km=100))
    )
    # 2) services sans lieu de déroulement
    services_remote = services.exclude(location_kinds__value="en-presentiel").annotate(
        distance=Value(None, output_field=IntegerField())
    )
    return list(services_on_site) + list(services_remote)


def multisort(lst, specs):
    # https://docs.python.org/3/howto/sorting.html#sort-stability-and-complex-sorts
    for key, reverse in reversed(specs):
        lst.sort(key=itemgetter(key), reverse=reverse)
    return lst


def _sort_services(services):
    services_on_site = [s for s in services if "en-presentiel" in s["location_kinds"]]
    random.shuffle(services_on_site)
    services_remote = [
        s for s in services if "en-presentiel" not in s["location_kinds"]
    ]
    random.shuffle(services_remote)

    results = sorted(services_on_site, key=itemgetter("distance")) + services_remote

    return results


def _get_di_results(
    di_client: data_inclusion.DataInclusionClient,
    city_code: str,
    categories: Optional[list[str]] = None,
    subcategories: Optional[list[str]] = None,
    kinds: Optional[list[str]] = None,
    fees: Optional[list[str]] = None,
) -> list:
    """Search data.inclusion services.

    The ``di_client`` acts as an entrypoint to the data.inclusion service repository.

    The search will target the sources configured by the ``DATA_INCLUSION_STREAM_SOURCES``
    environment variable.

    The other arguments match the input parameters from the classical search.

    This function essentially:

    * maps the input parameters,
    * offloads the search to the data.inclusion client,
    * maps the output results.

    This function should catch any client and upstream errors to prevent any impact on
    the classical flow of dora.

    Returns:
        A list of search results by SearchResultSerializer.
    """
    thematiques = []
    if categories is not None:
        thematiques += categories
    if subcategories is not None:
        thematiques += [subcat for subcat in subcategories if "--autre" not in subcat]

    # Si on recherche uniquement des sous-catégories `autre`, la liste des thématiques va être vide et d·i renverrait
    # *tous* les services. On renvoie donc plutôt une liste vide.
    if not thematiques and subcategories:
        return []

    try:
        raw_di_results = di_client.search_services(
            sources=settings.DATA_INCLUSION_STREAM_SOURCES,
            code_insee=city_code,
            thematiques=thematiques if len(thematiques) > 0 else None,
            types=kinds,
            frais=fees,
        )
    except requests.ConnectionError:
        return []

    if raw_di_results is None:
        return []

    raw_di_results = [
        result
        for result in raw_di_results
        if (
            result["service"]["date_suspension"] is None
            or date.fromisoformat(result["service"]["date_suspension"])
            > timezone.now().date()
        )
    ]

    # FIXME: exclude a few services which are not well managed yet
    raw_di_results = [
        result
        for result in raw_di_results
        if not (
            (
                result["service"]["latitude"] is None
                or result["service"]["longitude"] is None
            )
            and "en-presentiel" in result["service"]["modes_accueil"]
        )
    ]

    mapped_di_results = [
        data_inclusion.map_search_result(result) for result in raw_di_results
    ]

    return mapped_di_results


def _get_dora_results(
    request,
    city_code: str,
    categories: Optional[list[str]] = None,
    subcategories: Optional[list[str]] = None,
    kinds: Optional[list[str]] = None,
    fees: Optional[list[str]] = None,
):
    services = (
        models.Service.objects.published()
        .select_related(
            "structure",
        )
        .prefetch_related(
            "kinds",
            "categories",
            "subcategories",
        )
    )

    if kinds:
        services = services.filter(kinds__value__in=kinds)

    if fees:
        services = services.filter(fee_condition__value__in=fees)

    categories_filter = Q()
    if categories:
        categories_filter = Q(categories__value__in=categories)

    subcategories_filter = Q()
    if subcategories:
        for subcategory in subcategories:
            cat, subcat = subcategory.split("--")
            if subcat == "autre":
                # Quand on cherche une sous-catégorie de type 'Autre', on veut
                # aussi remonter les services sans sous-catégorie
                all_sister_subcats = models.ServiceSubCategory.objects.filter(
                    value__startswith=f"{cat}--"
                )
                subcategories_filter |= Q(subcategories__value=subcategory) | (
                    Q(categories__value=cat) & ~Q(subcategories__in=all_sister_subcats)
                )
            else:
                subcategories_filter |= Q(subcategories__value=subcategory)

    services = services.filter(categories_filter | subcategories_filter).distinct()

    geofiltered_services = filter_services_by_city_code(services, city_code)

    city_code = arrdt_to_main_insee_code(city_code)
    city = get_object_or_404(City, pk=city_code)

    # Exclude suspended services
    services_to_display = geofiltered_services.filter(
        Q(suspension_date=None) | Q(suspension_date__gte=timezone.now())
    ).distinct()

    results = _filter_and_annotate_dora_services(
        services_to_display,
        city.geom,
    )

    return SearchResultSerializer(results, many=True, context={"request": request}).data


def search_services(
    request,
    city_code: str,
    categories: Optional[list[str]] = None,
    subcategories: Optional[list[str]] = None,
    kinds: Optional[list[str]] = None,
    fees: Optional[list[str]] = None,
    di_client: Optional[data_inclusion.DataInclusionClient] = None,
) -> list[dict]:
    """Search services from all available repositories.

    It always includes results from dora own databases.

    If the ``di_client`` parameter is defined, results from data.inclusion will be
    added using the client dependency.

    Returns:
        A list of search results by SearchResultSerializer.
    """
    di_results = (
        _get_di_results(
            di_client=di_client,
            categories=categories,
            subcategories=subcategories,
            city_code=city_code,
            kinds=kinds,
            fees=fees,
        )
        if di_client is not None
        else []
    )

    dora_results = _get_dora_results(
        request=request,
        categories=categories,
        subcategories=subcategories,
        city_code=city_code,
        kinds=kinds,
        fees=fees,
    )

    all_results = [*dora_results, *di_results]
    return _sort_services(all_results)
