from django.conf import settings
from django.contrib import admin
from django.urls import include, path, register_converter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from rest_framework.routers import SimpleRouter
from rest_framework.versioning import NamespaceVersioning

import dora.admin_express.views
import dora.core.views
import dora.rest_auth
import dora.service_suggestions.views
import dora.services.views
import dora.sirene.views
import dora.stats.views
import dora.structures.views
import dora.support.views
import dora.users.views

from .url_converters import InseeCodeConverter, SiretConverter

router = SimpleRouter()
router.register(
    r"structures", dora.structures.views.StructureViewSet, basename="structure"
)
router.register(
    r"structure-members",
    dora.structures.views.StructureMemberViewset,
    basename="structure-member",
)
router.register(
    r"structure-putative-members",
    dora.structures.views.StructurePutativeMemberViewset,
    basename="structure-putative-member",
)
router.register(r"services", dora.services.views.ServiceViewSet, basename="service")
router.register(r"models", dora.services.views.ModelViewSet, basename="model")
router.register(
    r"services-suggestions",
    dora.service_suggestions.views.ServiceSuggestionViewSet,
    basename="service-suggestion",
)

router.register(
    r"structures-admin",
    dora.support.views.StructureAdminViewSet,
    basename="structure-admin",
)

router.register(
    r"services-admin",
    dora.support.views.ServiceAdminViewSet,
    basename="service-admin",
)

register_converter(InseeCodeConverter, "insee_code")
register_converter(SiretConverter, "siret")

public_api_patterns = [
    path("api/v1/", include("dora.api.urls_v1", namespace="v1")),
    path("api/v2/", include("dora.api.urls", namespace="v2")),
]

V1_CUSTOM_SETTINGS = {
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
    ],
}
spectacular_patterns = [
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(
            urlconf=public_api_patterns,
            api_version="v1",
            custom_settings=V1_CUSTOM_SETTINGS,
        ),
        name="schema-v1",
    ),
    path(
        "api/v2/schema/",
        SpectacularAPIView.as_view(urlconf=public_api_patterns, api_version="v2"),
        name="schema-v2",
    ),
    # Doc
    path(
        "api/v1/schema/doc/",
        SpectacularRedocView.as_view(
            url_name="schema-v1",
            versioning_class=NamespaceVersioning,
        ),
        name="api-doc-v1",
    ),
    path(
        "api/v2/schema/doc/",
        SpectacularRedocView.as_view(
            url_name="schema-v2",
            versioning_class=NamespaceVersioning,
        ),
        name="api-doc-v2",
    ),
]

private_api_patterns = [
    path("auth/", include("dora.rest_auth.urls")),
    path("search/", dora.services.views.search),
    path("stats/event/", dora.stats.views.log_event),
    path(
        "service-di/<slug:di_id>/",
        dora.services.views.service_di,
    ),
    path("admin-division-search/", dora.admin_express.views.search),
    path("admin-division-reverse-search/", dora.admin_express.views.reverse_search),
    path(
        "city-label/<insee_code:insee_code>/", dora.admin_express.views.get_city_label
    ),
    path("search-sirene/<insee_code:citycode>/", dora.sirene.views.search_sirene),
    path("search-siret/", dora.sirene.views.search_siret),
    path("search-all-sirene/", dora.sirene.views.search_all_sirene),
    path("services-options/", dora.services.views.options),
    path("siret-claimed/<siret:siret>/", dora.structures.views.siret_was_claimed),
    path("structures-options/", dora.structures.views.options),
    path("upload/<slug:structure_slug>/<str:filename>/", dora.core.views.upload),
    path("admin/", admin.site.urls),
    path("ping/", dora.core.views.ping),
    path("sentry-debug/", dora.core.views.trigger_error),
    path(
        "inclusion-connect-get-login-info/",
        dora.core.views.inclusion_connect_get_login_info,
    ),
    path(
        "inclusion-connect-get-logout-info/",
        dora.core.views.inclusion_connect_get_logout_info,
    ),
    path(
        "inclusion-connect-get-update-info/",
        dora.core.views.inclusion_connect_get_update_info,
    ),
    path(
        "inclusion-connect-authenticate/",
        dora.core.views.inclusion_connect_authenticate,
    ),
    path("admin-stats/", dora.support.views.stats),
    path("", include(router.urls)),
]

urlpatterns = [*private_api_patterns, *public_api_patterns, *spectacular_patterns]

if settings.PROFILE:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
