from django.contrib import admin

from .models import Category, ForecastRun, Prediction, TrafficData


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(TrafficData)
class TrafficDataAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "category", "views", "page_path", "created_at")
    list_filter = ("category", "date")
    search_fields = ("category__name", "page_path")
    date_hierarchy = "date"
    ordering = ("-date", "category__name")

    readonly_fields = ("created_at",)


@admin.register(ForecastRun)
class ForecastRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "forecast_days",
        "total_predictions",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "started_at")
    search_fields = ("error_message",)
    ordering = ("-started_at",)

    readonly_fields = (
        "started_at",
        "finished_at",
        "total_predictions",
        "error_message",
    )


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "prediction_date",
        "category",
        "predicted_views",
        "lower_bound",
        "upper_bound",
        "model_name",
        "forecast_run",
        "generated_at",
    )
    list_filter = ("category", "model_name", "prediction_date")
    search_fields = ("category__name", "model_name")
    date_hierarchy = "prediction_date"
    ordering = ("-prediction_date", "category__name")

    readonly_fields = ("generated_at",)