from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("upload/", views.upload_raw_data, name="upload_raw_data"),
    path("forecast/generate/", views.generate_forecast_view, name="generate_forecast"),
]