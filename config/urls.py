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
from django.urls import include, path
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter

import dora.core.views
import dora.structures.views

router = DefaultRouter()
router.register(r"structures", dora.structures.views.StructureViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("hello/", dora.core.views.hello_world),
    path("admin/", admin.site.urls),
    path("api-token-auth/", views.obtain_auth_token),
]
