"""dora URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path, register_converter
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter

import dora.core.views
import dora.services.views
import dora.sirene.views
import dora.structures.views
import dora.users.views

router = DefaultRouter()
router.register(r"structures", dora.structures.views.StructureViewSet)
router.register(r"services", dora.services.views.ServiceViewSet)


class InseeCodeConverter:
    regex = r"\d[0-9aAbB]\d{3}"

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return f"{value}"


register_converter(InseeCodeConverter, "insee_code")


class SiretConverter:
    regex = r"\d{14}"

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return f"{value}"


register_converter(SiretConverter, "siret")

urlpatterns = [
    path("", include(router.urls)),
    path("me/", dora.users.views.me),
    path("services-options/", dora.services.views.options),
    path("structures-options/", dora.structures.views.options),
    path("search/", dora.services.views.search),
    path("upload/<slug:structure_slug>/<str:filename>/", dora.core.views.upload),
    path("search-sirene/<insee_code:citycode>/", dora.sirene.views.search_sirene),
    path("search-all-sirene/", dora.sirene.views.search_all_sirene),
    path("siret-claimed/<siret:siret>/", dora.structures.views.siret_was_claimed),
    path("admin/", admin.site.urls),
    path("api-token-auth/", views.obtain_auth_token),
    path("sentry-debug/", dora.core.views.trigger_error),
]
