from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r"structures", views.StructureViewSetV1, basename="structure")
router.register(
    r"structure-typologies",
    views.StructureTypologyViewSetV1,
    basename="structure-typology",
)
router.register(
    r"structure-sources",
    views.StructureSourceViewSetV1,
    basename="structure-source",
)
router.register(r"services", views.ServiceViewSetV1, basename="service")
router.register(
    r"service-categories",
    views.ServiceCategoryViewSetV1,
    basename="service-category",
)
router.register(
    r"service-subcategories",
    views.ServiceSubCategoryViewSetV1,
    basename="service-subcategory",
)
router.register(
    r"service-kinds",
    views.ServiceKindViewSetV1,
    basename="service-kind",
)
router.register(
    r"service-beneficiary-access-modes",
    views.BeneficiaryAccessModeViewSetV1,
    basename="service-beneficiary-access-mode",
)
router.register(
    r"service-coach-orientation-modes",
    views.CoachOrientationModeViewSetV1,
    basename="service-coach-orientation-mode",
)
router.register(
    r"service-location-kinds",
    views.LocationKindViewSetV1,
    basename="service-location-kind",
)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "api"
