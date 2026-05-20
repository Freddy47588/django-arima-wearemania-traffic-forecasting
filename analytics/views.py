import json

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render, redirect

from analytics.models import Category, TrafficData, Prediction, ForecastRun
from analytics.services.forecasting import generate_all_forecasts


def dashboard(request):
    selected_category = request.GET.get("category")

    categories = Category.objects.all()

    traffic_queryset = TrafficData.objects.select_related("category").all()

    if selected_category:
        traffic_queryset = traffic_queryset.filter(category_id=selected_category)

    actual_grouped = {}

    for item in traffic_queryset.values("date", "views").order_by("date"):
        date_str = item["date"].strftime("%Y-%m-%d")
        actual_grouped[date_str] = actual_grouped.get(date_str, 0) + item["views"]

    actual_labels = list(actual_grouped.keys())
    actual_views = list(actual_grouped.values())

    latest_forecast_run = (
        ForecastRun.objects
        .filter(status="success")
        .order_by("-created_at")
        .first()
    )

    prediction_queryset = Prediction.objects.none()

    if latest_forecast_run:
        prediction_queryset = Prediction.objects.filter(
            forecast_run=latest_forecast_run
        ).select_related("category")

        if selected_category:
            prediction_queryset = prediction_queryset.filter(
                category_id=selected_category
            )

    forecast_labels = [
        item.prediction_date.strftime("%Y-%m-%d")
        for item in prediction_queryset.order_by("prediction_date")
    ]

    forecast_views = [
        item.predicted_views
        for item in prediction_queryset.order_by("prediction_date")
    ]

    forecast_lower = [
        item.lower_bound
        for item in prediction_queryset.order_by("prediction_date")
    ]

    forecast_upper = [
        item.upper_bound
        for item in prediction_queryset.order_by("prediction_date")
    ]

    top_forecast_categories = []

    if latest_forecast_run:
        top_forecast_categories = (
            Prediction.objects
            .filter(forecast_run=latest_forecast_run)
            .values("category__name")
            .annotate(total_predicted_views=Sum("predicted_views"))
            .order_by("-total_predicted_views")[:3]
        )

    total_actual_views = sum(actual_views)
    total_forecast_views = sum(forecast_views)

    context = {
        "categories": categories,
        "selected_category": selected_category,

        "actual_labels": json.dumps(actual_labels),
        "actual_views": json.dumps(actual_views),

        "forecast_labels": json.dumps(forecast_labels),
        "forecast_views": json.dumps(forecast_views),
        "forecast_lower": json.dumps(forecast_lower),
        "forecast_upper": json.dumps(forecast_upper),

        "total_actual_views": total_actual_views,
        "total_forecast_views": total_forecast_views,

        "latest_forecast_run": latest_forecast_run,
        "top_forecast_categories": top_forecast_categories,
    }

    return render(request, "analytics/dashboard.html", context)


def generate_forecast_view(request):
    if request.method == "POST":
        try:
            forecast_run = generate_all_forecasts(forecast_days=7)

            messages.success(
                request,
                f"Forecast berhasil dibuat. Total prediksi: {forecast_run.total_predictions}"
            )

        except Exception as error:
            messages.error(
                request,
                f"Forecast gagal dibuat: {error}"
            )

    return redirect("dashboard")