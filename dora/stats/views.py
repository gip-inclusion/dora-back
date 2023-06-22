from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.core.utils import code_insee_to_code_dept, get_object_or_none
from dora.services.models import Service, ServiceCategory, ServiceSubCategory
from dora.stats.models import (
    ABTestGroup,
    MobilisationEvent,
    SearchView,
    ServiceView,
    StructureView,
)
from dora.structures.models import Structure, StructureMember

from .models import PageView


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def log_event(request):
    tag = request.data.get("tag")
    service_slug = request.data.get("service", "")
    structure_slug = request.data.get("structure", "")
    service = structure = None
    if service_slug:
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
    }

    structure_membership = (
        StructureMember.objects.filter(structure_id=structure.id, user=user).first()
        if structure
        else None
    )
    structure_data = {
        "structure": structure,
        "structure_slug": structure_slug,
        "is_structure_member": structure_membership is not None,
        "is_structure_admin": structure_membership.is_admin
        if structure_membership
        else False,
        "structure_department": structure.department if structure else "",
        "structure_city_code": structure.city_code if structure else "",
    }

    service_data = {
        "service": service,
        "service_slug": service_slug,
        "update_status": service.get_update_status() if service else "",
        "status": service.status if service else "",
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
        )
        categories_values = request.data.get("category_ids", "")
        categories = ServiceCategory.objects.filter(value__in=categories_values)
        subcategories_values = request.data.get("sub_category_ids", "")
        # TODO: est-ce qu'on veut aussi ajouter les categories de ces sous-categories dans la liste des categorie set vice versa?
        subcategories = ServiceSubCategory.objects.filter(
            value__in=subcategories_values
        )
        searchevent.categories.set(categories)
        searchevent.subcategories.set(subcategories)
    elif tag == "structure":
        StructureView.objects.create(**common_analytics_data, **structure_data)
    elif tag == "service":
        ServiceView.objects.create(
            **common_analytics_data, **structure_data, **service_data
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
    return Response(status=204)
