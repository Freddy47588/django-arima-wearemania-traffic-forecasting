import json
import re

import pandas as pd
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.utils.text import slugify

from analytics.models import Category, TrafficData, Prediction, ForecastRun, ImportLog
from analytics.services.forecasting import generate_all_forecasts


def map_category_from_path(page_path):
    """
    Mapping sederhana URL path ke kategori berita.
    Bisa kamu kembangkan lagi sesuai struktur URL Wearemania.
    """

    if not page_path:
        return "Uncategorized"

    path = str(page_path).lower()

    # Bersihkan query string dan hash
    path = path.split("?")[0].split("#")[0]

    # Ambil segmen URL
    segments = [segment for segment in path.split("/") if segment]

    if not segments:
        return "Uncategorized"

    ignored_segments = [
        "page",
        "tag",
        "author",
        "search",
        "wp-content",
        "wp-admin",
        "feed",
        "amp",
    ]

    for segment in segments:
        if segment not in ignored_segments and not segment.isdigit():
            category = segment.replace("-", " ").replace("_", " ")
            category = re.sub(r"\s+", " ", category).strip()
            return category.title()

    return "Uncategorized"


def normalize_csv_columns(df):
    """
    Menyamakan nama kolom dari CSV agar bisa diproses.
    Mendukung beberapa variasi nama kolom dari GA4/export CSV.
    """

    column_mapping = {}

    for col in df.columns:
        clean_col = col.strip().lower()

        if clean_col in ["date", "tanggal"]:
            column_mapping[col] = "date"

        elif clean_col in [
            "page path",
            "pagepath",
            "page_path",
            "path",
            "url path",
            "landing page",
        ]:
            column_mapping[col] = "page_path"

        elif clean_col in [
            "views",
            "screen page views",
            "screenpageviews",
            "page views",
            "pageviews",
            "total users",
            "active users",
        ]:
            column_mapping[col] = "views"

    df = df.rename(columns=column_mapping)

    return df


def upload_raw_data(request):
    """
    Upload CSV traffic Wearemania.
    Data CSV akan disimpan ke TrafficData dan dikategorikan berdasarkan page_path.
    """

    if request.method == "POST":
        uploaded_file = (
            request.FILES.get("csv_file")
            or request.FILES.get("file")
            or request.FILES.get("dataset")
        )

        if not uploaded_file:
            messages.error(request, "File CSV belum dipilih.")
            return redirect("upload_raw_data")

        if not uploaded_file.name.lower().endswith(".csv"):
            messages.error(request, "Format file harus CSV.")
            return redirect("upload_raw_data")

        try:
            df = pd.read_csv(uploaded_file)
            total_rows = len(df)

            df = normalize_csv_columns(df)

            required_columns = ["date", "page_path", "views"]
            missing_columns = [
                column for column in required_columns
                if column not in df.columns
            ]

            if missing_columns:
                messages.error(
                    request,
                    f"Kolom CSV tidak lengkap. Kolom wajib: date, page_path, views. "
                    f"Kolom yang belum ada: {', '.join(missing_columns)}"
                )
                return redirect("upload_raw_data")

            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
            df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
            df["page_path"] = df["page_path"].astype(str)

            # Hapus data tidak valid
            df = df.dropna(subset=["date"])
            df = df[df["views"] >= 0]

            imported_rows = 0
            skipped_rows = total_rows - len(df)

            for _, row in df.iterrows():
                page_path = row["page_path"]
                category_name = map_category_from_path(page_path)

                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={"slug": slugify(category_name)}
                )

                TrafficData.objects.create(
                    category=category,
                    date=row["date"],
                    page_path=page_path,
                    views=int(row["views"]),
                )

                imported_rows += 1

            ImportLog.objects.create(
                filename=uploaded_file.name,
                total_rows=total_rows,
                imported_rows=imported_rows,
                skipped_rows=skipped_rows,
                status="success",
                message=f"Import berhasil. {imported_rows} data disimpan."
            )

            messages.success(
                request,
                f"Import berhasil. {imported_rows} data disimpan. "
                f"{skipped_rows} data dilewati."
            )

            return redirect("dashboard")

        except Exception as error:
            ImportLog.objects.create(
                filename=uploaded_file.name,
                total_rows=0,
                imported_rows=0,
                skipped_rows=0,
                status="failed",
                message=str(error)
            )

            messages.error(request, f"Import gagal: {error}")
            return redirect("upload_raw_data")

    return render(request, "analytics/upload_raw_data.html")


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