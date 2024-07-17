from django.urls import path

import dora.oidc.views as views

oidc_patterns = [
    path(
        "inclusion-connect-get-login-info/",
        views.inclusion_connect_get_login_info,
    ),
    path(
        "inclusion-connect-get-logout-info/",
        views.inclusion_connect_get_logout_info,
    ),
    path(
        "inclusion-connect-get-update-info/",
        views.inclusion_connect_get_update_info,
    ),
    path(
        "inclusion-connect-authenticate/",
        views.inclusion_connect_authenticate,
    ),
]

# Prendront la place de `oidc_patterns`,
# une fois Inclusion-Connect décommissionné.
proconnect_patterns = [
    path("oidc/authorize", views.oidc_authorize),
    path("oidc/logout", views.oidc_logout),
    # ...
]
