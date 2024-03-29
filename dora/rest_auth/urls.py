from django.urls import path

from . import views

urlpatterns = [
    path("user-info/", views.user_info),
    path("join-structure/", views.join_structure),
    path("invite-first-admin/", views.invite_first_admin),
    path("accept-cgu/", views.accept_cgu),
]
