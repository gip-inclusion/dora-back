from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r"structures", views.StructureViewSet, basename="structure")
router.register(r"services", views.ServiceViewSet, basename="service")


urlpatterns = [
    path("", include(router.urls)),
]

urlpatterns.extend(
    [
        path("schema/", SpectacularAPIView.as_view(urlconf=urlpatterns), name="schema"),
        # Optional UI:
        path(
            "schema/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]
)
