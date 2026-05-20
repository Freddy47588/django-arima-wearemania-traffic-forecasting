from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        login_required(views.dashboard),
        name="dashboard",
    ),

    path(
        "upload/",
        login_required(views.upload_raw_data),
        name="upload_raw_data",
    ),
]