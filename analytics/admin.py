from django.contrib import admin

from .models import Category, TrafficData, Prediction, ForecastRun, ImportLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")


@admin.register(TrafficData)
class TrafficDataAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "category", "views")
    list_filter = ("category", "date")
    search_fields = ("page_path", "category__name")
    date_hierarchy = "date"


@admin.register(ForecastRun)
class ForecastRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "model_name",
        "forecast_days",
        "status",
        "total_predictions",
        "created_at",
        "finished_at",
    )
    list_filter = ("status", "model_name")
    search_fields = ("message",)


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "forecast_run",
        "category",
        "prediction_date",
        "predicted_views",
        "lower_bound",
        "upper_bound",
        "model_order",
    )
    list_filter = ("category", "model_order", "prediction_date")
    search_fields = ("category__name",)
    date_hierarchy = "prediction_date"


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "filename",
        "total_rows",
        "imported_rows",
        "skipped_rows",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("filename", "message")