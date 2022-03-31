from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r"structures", views.StructureViewSet, basename="structure")
router.register(
    r"structure-typologies",
    views.StructureTypologyViewSet,
    basename="structure-typology",
)
router.register(
    r"structure-sources",
    views.StructureSourceViewSet,
    basename="structure-source",
)
router.register(r"services", views.ServiceViewSet, basename="service")
router.register(
    r"service-categories",
    views.ServiceCategoryViewSet,
    basename="service-category",
)
router.register(
    r"service-subcategories",
    views.ServiceSubCategoryViewSet,
    basename="service-subcategory",
)
router.register(
    r"service-kinds",
    views.ServiceKindViewSet,
    basename="service-kind",
)
router.register(
    r"service-beneficiary-access-modes",
    views.BeneficiaryAccessModeViewSet,
    basename="service-beneficiary-access-mode",
)
router.register(
    r"service-coach-orientation-modes",
    views.CoachOrientationModeViewSet,
    basename="service-coach-orientation-mode",
)
router.register(
    r"service-location-kinds",
    views.LocationKindViewSet,
    basename="service-location-kind",
)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "api"
