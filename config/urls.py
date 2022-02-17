from django.contrib import admin
from django.urls import include, path, register_converter
from rest_framework.routers import SimpleRouter

import dora.admin_express.views
import dora.core.views
import dora.rest_auth
import dora.service_suggestions.views
import dora.services.views
import dora.sirene.views
import dora.structures.views
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
router.register(
    r"services-suggestions",
    dora.service_suggestions.views.ServiceSuggestionViewSet,
    basename="service-suggestion",
)
register_converter(InseeCodeConverter, "insee_code")
register_converter(SiretConverter, "siret")


urlpatterns = [
    path("auth/", include("dora.rest_auth.urls")),
    path("search/", dora.services.views.search),
    path("profile/change/", dora.users.views.update_profile),
    path("profile/password/change/", dora.users.views.password_change),
    path("admin-division-search/", dora.admin_express.views.search),
    path("search-sirene/<insee_code:citycode>/", dora.sirene.views.search_sirene),
    path("search-safir/", dora.structures.views.search_safir),
    path("search-siret/", dora.sirene.views.search_siret),
    path("search-all-sirene/", dora.sirene.views.search_all_sirene),
    path("services-options/", dora.services.views.options),
    path("siret-claimed/<siret:siret>/", dora.structures.views.siret_was_claimed),
    path("structures-options/", dora.structures.views.options),
    path("upload/<slug:structure_slug>/<str:filename>/", dora.core.views.upload),
    path("admin/", admin.site.urls),
    path("ping/", dora.core.views.ping),
    path("sentry-debug/", dora.core.views.trigger_error),
    path("", include(router.urls)),
]
