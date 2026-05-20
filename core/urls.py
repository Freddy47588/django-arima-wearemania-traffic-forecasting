"""
URL configuration for Wearemania Traffic Forecasting Dashboard.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(
            next_page="login",
        ),
        name="logout",
    ),

    # Main app
    path("", include("analytics.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)