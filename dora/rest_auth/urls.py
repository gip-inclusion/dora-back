from django.urls import path

from . import views

urlpatterns = [
    path("user-info/", views.user_info),
    path("join-structure/", views.join_structure),
]
