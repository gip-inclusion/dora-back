from django.conf import settings
from django.contrib import admin
from django.urls import include, path, register_converter
from rest_framework.routers import SimpleRouter

import dora.admin_express.views
import dora.core.views
import dora.orientations.views
import dora.service_suggestions.views
import dora.services.views
import dora.sirene.views
import dora.stats.views
import dora.structures.views
import dora.support.views
import dora.users.views
from dora import data_inclusion
from dora.oidc.urls import oidc_patterns

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
router.register(r"bookmarks", dora.services.views.BookmarkViewSet, basename="bookmark")
router.register(r"models", dora.services.views.ModelViewSet, basename="model")
router.register(
    r"saved-searches", dora.services.views.SavedSearchViewSet, basename="saved-search"
)

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
router.register(
    r"orientations",
    dora.orientations.views.OrientationViewSet,
    basename="orientation",
)

register_converter(InseeCodeConverter, "insee_code")
register_converter(SiretConverter, "siret")


# conditionally inject a di_client dependency to views
di_client = data_inclusion.di_client_factory() if not settings.IS_TESTING else None

private_api_patterns = [
    path("auth/", include("dora.rest_auth.urls")),
    path("search/", dora.services.views.search, {"di_client": di_client}),
    path("stats/event/", dora.stats.views.log_event),
    path(
        "services-di/<slug:di_id>/",
        dora.services.views.service_di,
        {"di_client": di_client},
    ),
    path(
        "services-di/<slug:di_id>/share/",
        dora.services.views.share_di_service,
        {"di_client": di_client},
    ),
    path("admin-division-search/", dora.admin_express.views.search),
    path("admin-division-reverse-search/", dora.admin_express.views.reverse_search),
    path("admin-division-departments/", dora.admin_express.views.get_departments),
    path(
        "city-label/<insee_code:insee_code>/", dora.admin_express.views.get_city_label
    ),
    path("search-sirene/<insee_code:citycode>/", dora.sirene.views.search_sirene),
    path("search-siret/", dora.sirene.views.search_siret),
    path("search-safir/", dora.sirene.views.search_safir),
    path("search-all-sirene/", dora.sirene.views.search_all_sirene),
    path("services-options/", dora.services.views.options),
    path("siret-claimed/<siret:siret>/", dora.structures.views.siret_was_claimed),
    path("structures-options/", dora.structures.views.options),
    path("upload/<slug:structure_slug>/<str:filename>/", dora.core.views.upload),
    path("safe-upload/<str:filename>/", dora.core.views.safe_upload),
    path("admin/", admin.site.urls),
    path("ping/", dora.core.views.ping),
    path("sentry-debug/", dora.core.views.trigger_error),
    path("", include(router.urls)),
    path("profile/", dora.users.views.update_user_profile),
    path(
        "profile/main-activity/", dora.users.views.update_user_profile
    ),  # TODO: remove when not used by frontend anymore
]

di_api_patterns = [
    path("api/v2/", include("dora.api.urls", namespace="v2")),
]


urlpatterns = [
    *private_api_patterns,
    *di_api_patterns,
    *oidc_patterns,
]

if settings.PROFILE:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
