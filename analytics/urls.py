from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("forecast/generate/", views.generate_forecast_view, name="generate_forecast"),
]