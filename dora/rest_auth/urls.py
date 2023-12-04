from django.urls import path

from . import views

urlpatterns = [
    path("user-info/", views.user_info),
    path("join-structure/", views.join_structure),
    path("invite-admin/", views.invite_admin),
    path("accept-cgu/", views.accept_cgu),
]
