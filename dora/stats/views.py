from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.core.utils import code_insee_to_code_dept, get_object_or_none
from dora.orientations.models import Orientation
from dora.services.models import Service, ServiceCategory, ServiceSubCategory
from dora.stats.models import (
    ABTestGroup,
    DiMobilisationEvent,
    DiServiceView,
    MobilisationEvent,
    OrientationView,
    SearchView,
    ServiceView,
    StructureView,
)
from dora.structures.models import Structure, StructureMember

from .models import PageView


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def log_event(request):
    def get_categories(cats_values, subcats_values):
        # On loggue également toutes les catégories des sous-catégories demandées
        subcats_cats_values = set(subcat.split("--")[0] for subcat in subcats_values)

        all_categories = ServiceCategory.objects.filter(
            Q(value__in=cats_values) | Q(value__in=subcats_cats_values)
        )

        all_subcategories = ServiceSubCategory.objects.filter(value__in=subcats_values)
        for category_value in cats_values:
            all_subcategories |= ServiceSubCategory.objects.filter(
                value__startswith=category_value
            )
        return all_categories, all_subcategories

    tag = request.data.get("tag")
    service_slug = request.data.get("service", "")
    structure_slug = request.data.get("structure", "")
    service = structure = orientation = None
    orientation_id = request.data.get("orientation", "")
    num_di_results = int(request.data.get("num_di_results", "0"))
    num_di_results_top10 = int(request.data.get("num_di_results_top10", "0"))

    if orientation_id:
        orientation = get_object_or_none(Orientation, id=orientation_id)
        if orientation:
            service = orientation.service
            structure = orientation.service.structure
    if not service and service_slug:
        service = get_object_or_none(Service, slug=service_slug)
        if service:
            structure = service.structure
    if not structure and structure_slug:
        structure = get_object_or_none(Structure, slug=structure_slug)

    is_search = tag == "search"
    search_city_code = request.data.get("search_city_code", "") if is_search else ""
    search_department = (
        code_insee_to_code_dept(search_city_code) if search_city_code else ""
    )
    search_num_results = request.data.get("search_num_results") if is_search else None
    user = request.user

    common_analytics_data = {
        "path": request.data.get("path"),
        "user": user if user.is_authenticated else None,
        "is_logged": user.is_authenticated,
        "is_staff": user.is_staff,
        "is_manager": user.is_manager if user.is_authenticated else False,
        "is_an_admin": StructureMember.objects.filter(user=user, is_admin=True).exists()
        if user.is_authenticated
        else False,
        "user_kind": user.main_activity if user.is_authenticated else "",
        "anonymous_user_hash": request.data.get("user_hash", ""),
    }

    structure_membership = (
        StructureMember.objects.filter(structure_id=structure.id, user=user).first()
        if structure and user.is_authenticated
        else None
    )
    structure_data = {
        "structure": structure,
        "is_structure_member": structure_membership is not None,
        "is_structure_admin": structure_membership.is_admin
        if structure_membership
        else False,
        "structure_department": structure.department if structure else "",
        "structure_city_code": structure.city_code if structure else "",
        "structure_source": structure.source.value
        if structure and structure.source
        else "",
    }

    service_data = {
        "service": service,
        "update_status": service.get_update_status() if service else "",
        "status": service.status if service else "",
        "service_source": service.source.value if service and service.source else "",
        "is_orientable": True if service and service.is_orientable() is True else False,
    }

    di_service_data = {
        "structure_id": request.data.get("di_structure_id", ""),
        "structure_name": request.data.get("di_structure_name", ""),
        "structure_department": request.data.get("di_structure_department", ""),
        "service_id": request.data.get("di_service_id", ""),
        "service_name": request.data.get("di_service_name", ""),
        "source": request.data.get("di_source", ""),
    }

    if tag == "pageview":
        PageView.objects.create(
            **common_analytics_data,
            title=request.data.get("title", ""),
        )

    elif tag == "search":
        searchevent = SearchView.objects.create(
            **common_analytics_data,
            city_code=search_city_code,
            department=search_department,
            num_results=search_num_results,
            num_di_results=num_di_results,
            num_di_results_top10=num_di_results_top10,
        )
        cats_values = request.data.get("category_ids", [])
        subcats_values = request.data.get("sub_category_ids", [])
        categories, subcategories = get_categories(cats_values, subcats_values)
        searchevent.categories.set(categories)
        searchevent.subcategories.set(subcategories)
    elif tag == "structure":
        StructureView.objects.create(**common_analytics_data, **structure_data)
    elif tag == "service":
        ServiceView.objects.create(
            **common_analytics_data, **structure_data, **service_data
        )
    elif tag == "di_service":
        di_view = DiServiceView.objects.create(
            **common_analytics_data, **di_service_data
        )
        cats_values = request.data.get("di_categories", [])
        subcats_values = request.data.get("di_subcategories", [])
        categories, subcategories = get_categories(cats_values, subcats_values)
        di_view.categories.set(categories)
        di_view.subcategories.set(subcategories)
    elif tag == "orientation":
        OrientationView.objects.create(
            orientation=orientation,
            orientation_status=orientation.status,
            **common_analytics_data,
            **structure_data,
            **service_data,
        )
    elif tag == "mobilisation":
        mev = MobilisationEvent.objects.create(
            **common_analytics_data, **structure_data, **service_data
        )
        ab_testing_group = request.data.get("ab_testing_group", "")
        if ab_testing_group:
            ab_testing_group, _created = ABTestGroup.objects.get_or_create(
                value=ab_testing_group
            )
            mev.ab_test_groups.set([ab_testing_group])

    elif tag == "di_mobilisation":
        di_mev = DiMobilisationEvent.objects.create(
            **common_analytics_data, **di_service_data
        )
        ab_testing_group = request.data.get("ab_testing_group", "")
        if ab_testing_group:
            ab_testing_group, _created = ABTestGroup.objects.get_or_create(
                value=ab_testing_group
            )
            di_mev.ab_test_groups.set([ab_testing_group])
        cats_values = request.data.get("di_categories", [])
        subcats_values = request.data.get("di_subcategories", [])
        categories, subcategories = get_categories(cats_values, subcats_values)
        di_mev.categories.set(categories)
        di_mev.subcategories.set(subcategories)
    return Response(status=204)
