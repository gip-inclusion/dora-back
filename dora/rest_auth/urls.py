from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login),
    path("password/reset/", views.password_reset),
    path("password/reset/confirm/", views.password_reset_confirm),
    path("token/verify/", views.token_verify),
    path("user-info/", views.user_info),
    path("register-structure-and-user/", views.register_structure_and_user),
    path("registration/validate-email/", views.validate_email),
    path("registration/resend-validation-email/", views.resend_validation_email),
]
