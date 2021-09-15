from django.urls import path

from . import views

urlpatterns = [
    # path("me/", dora.users.views.me),
    path("login/", views.login),
    path("password/reset/", views.password_reset),
    path("password/reset/confirm/", views.password_reset_confirm),
    path("password/change/", views.password_change),
    path("token/verify/", views.token_verify),
    path("registration/", views.register),
    path("registration/verify-email", views.verify_email),
    path("registration/resend-email", views.resend_email),
]
