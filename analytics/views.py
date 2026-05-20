import json
from datetime import datetime

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render

from .forms import CSVUploadForm
from .models import Category, ForecastRun, Prediction, TrafficData


def normalize_column_name(column_name):
    return (
        str(column_name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_column(columns, possible_names):
    normalized_map = {
        normalize_column_name(column): column
        for column in columns
    }

    for name in possible_names:
        normalized_name = normalize_column_name(name)

        if normalized_name in normalized_map:
            return normalized_map[normalized_name]

    return None


def clean_page_path(page_path):
    if pd.isna(page_path):
        return "/"

    page_path = str(page_path).strip()

    if not page_path:
        return "/"

    if page_path.startswith("http://") or page_path.startswith("https://"):
        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(page_path)
            page_path = parsed_url.path or "/"
        except Exception:
            pass

    if not page_path.startswith("/"):
        page_path = f"/{page_path}"

    return page_path.lower()


def detect_category_from_path(page_path):
    path = clean_page_path(page_path)

    category_rules = {
        "Berita Arema": [
            "/berita-arema",
            "/arema-news",
            "/arema-fc",
        ],
        "Aremaday": [
            "/aremaday",
            "/arema-day",
        ],
        "Aremania": [
            "/aremania",
        ],
        "Memori Arema": [
            "/memori-arema",
        ],
        "Arema Putri": [
            "/arema-putri",
        ],
        "Ngalam": [
            "/ngalam",
        ],
        "Fokus": [
            "/fokus",
        ],
        "Nasional": [
            "/nasional",
        ],
        "Liga 1": [
            "/liga-1",
            "/bri-liga-1",
        ],
        "Timnas": [
            "/timnas",
            "/tim-nasional",
        ],
        "Kriminal": [
            "/kriminal",
        ],
        "Pendidikan": [
            "/pendidikan",
        ],
        "Ekonomi": [
            "/ekonomi",
        ],
        "Politik": [
            "/politik",
        ],
    }

    for category_name, keywords in category_rules.items():
        for keyword in keywords:
            if keyword in path:
                return category_name

    return "Lainnya"


def parse_date_value(value):
    if pd.isna(value):
        return None

    if isinstance(value, datetime):
        return value.date()

    value = str(value).strip()

    if not value:
        return None

    possible_formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y%m%d",
    ]

    for date_format in possible_formats:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    try:
        parsed_date = pd.to_datetime(value, errors="coerce")

        if pd.isna(parsed_date):
            return None

        return parsed_date.date()
    except Exception:
        return None


@login_required
def dashboard(request):
    selected_category = request.GET.get("category")

    categories = Category.objects.all()

    traffic_queryset = TrafficData.objects.select_related("category").all()

    latest_forecast_run = (
        ForecastRun.objects
        .filter(status=ForecastRun.STATUS_SUCCESS)
        .order_by("-started_at")
        .first()
    )

    prediction_queryset = Prediction.objects.select_related("category").all()

    if latest_forecast_run:
        prediction_queryset = prediction_queryset.filter(
            forecast_run=latest_forecast_run
        )

    if selected_category:
        traffic_queryset = traffic_queryset.filter(category_id=selected_category)
        prediction_queryset = prediction_queryset.filter(category_id=selected_category)

    actual_grouped = {}

    for item in traffic_queryset.values("date", "views").order_by("date"):
        date_str = item["date"].strftime("%Y-%m-%d")
        actual_grouped[date_str] = actual_grouped.get(date_str, 0) + item["views"]

    actual_labels = list(actual_grouped.keys())
    actual_views = list(actual_grouped.values())

    forecast_grouped = {}

    for item in prediction_queryset.values("prediction_date", "predicted_views").order_by("prediction_date"):
        date_str = item["prediction_date"].strftime("%Y-%m-%d")
        forecast_grouped[date_str] = forecast_grouped.get(date_str, 0) + item["predicted_views"]

    forecast_labels = list(forecast_grouped.keys())
    forecast_views = list(forecast_grouped.values())

    total_actual_views = sum(actual_views)
    total_forecast_views = sum(forecast_views)

    total_categories = categories.count()
    total_traffic_data = TrafficData.objects.count()

    top_actual_categories = (
        traffic_queryset
        .values("category__name")
        .annotate(total_views=Sum("views"))
        .order_by("-total_views")[:5]
    )

    top_forecast_categories = (
        prediction_queryset
        .values("category__name")
        .annotate(total_predicted_views=Sum("predicted_views"))
        .order_by("-total_predicted_views")[:5]
    )

    last_prediction = (
        Prediction.objects
        .select_related("category")
        .order_by("-generated_at")
        .first()
    )

    context = {
        "categories": categories,
        "selected_category": selected_category,

        "actual_labels": json.dumps(actual_labels),
        "actual_views": json.dumps(actual_views),
        "forecast_labels": json.dumps(forecast_labels),
        "forecast_views": json.dumps(forecast_views),

        "total_actual_views": total_actual_views,
        "total_forecast_views": total_forecast_views,
        "total_categories": total_categories,
        "total_traffic_data": total_traffic_data,

        "top_actual_categories": top_actual_categories,
        "top_forecast_categories": top_forecast_categories,

        "latest_forecast_run": latest_forecast_run,
        "last_prediction": last_prediction,
    }

    return render(request, "analytics/dashboard.html", context)


@login_required
def upload_raw_data(request):
    form = CSVUploadForm()

    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)

        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]

            try:
                df = pd.read_csv(csv_file)

                if df.empty:
                    messages.error(request, "File CSV kosong. Tidak ada data yang bisa diimport.")
                    return redirect("upload_raw_data")

                date_column = find_column(
                    df.columns,
                    [
                        "date",
                        "tanggal",
                        "day",
                        "Date",
                        "Tanggal",
                    ],
                )

                path_column = find_column(
                    df.columns,
                    [
                        "page_path",
                        "path",
                        "url",
                        "url_path",
                        "page",
                        "pagePath",
                        "Page path",
                        "Page Path",
                        "Landing page",
                        "landing_page",
                    ],
                )

                views_column = find_column(
                    df.columns,
                    [
                        "views",
                        "screen_page_views",
                        "page_views",
                        "pageviews",
                        "total_views",
                        "Views",
                        "Page views",
                        "Screen page views",
                    ],
                )

                missing_columns = []

                if not date_column:
                    missing_columns.append("date")

                if not path_column:
                    missing_columns.append("page_path")

                if not views_column:
                    missing_columns.append("views")

                if missing_columns:
                    messages.error(
                        request,
                        (
                            "Kolom CSV tidak lengkap. "
                            "Kolom wajib: date, page_path, views. "
                            f"Kolom yang belum ditemukan: {', '.join(missing_columns)}."
                        ),
                    )
                    return redirect("upload_raw_data")

                created_count = 0
                skipped_count = 0

                traffic_objects = []

                for _, row in df.iterrows():
                    traffic_date = parse_date_value(row.get(date_column))
                    page_path = clean_page_path(row.get(path_column))

                    try:
                        views = int(float(row.get(views_column, 0)))
                    except (TypeError, ValueError):
                        views = 0

                    if not traffic_date or views < 0:
                        skipped_count += 1
                        continue

                    category_name = detect_category_from_path(page_path)

                    category, _ = Category.objects.get_or_create(
                        name=category_name
                    )

                    traffic_objects.append(
                        TrafficData(
                            category=category,
                            date=traffic_date,
                            page_path=page_path,
                            views=views,
                        )
                    )

                if not traffic_objects:
                    messages.error(
                        request,
                        "Tidak ada data valid yang berhasil diproses dari CSV."
                    )
                    return redirect("upload_raw_data")

                TrafficData.objects.bulk_create(traffic_objects, batch_size=1000)
                created_count = len(traffic_objects)

                first_date = min(item.date for item in traffic_objects)
                last_date = max(item.date for item in traffic_objects)
                total_categories = Category.objects.count()

                messages.success(
                    request,
                    (
                        f"Import berhasil. {created_count} data harian kategori disimpan. "
                        f"Periode {first_date} sampai {last_date}. "
                        f"Total kategori: {total_categories}."
                    ),
                )

                if skipped_count > 0:
                    messages.warning(
                        request,
                        f"{skipped_count} baris dilewati karena tanggal/views tidak valid."
                    )

                return redirect("upload_raw_data")

            except Exception as error:
                messages.error(
                    request,
                    f"Gagal memproses CSV: {error}"
                )
                return redirect("upload_raw_data")

    latest_upload = (
        TrafficData.objects
        .select_related("category")
        .order_by("-created_at")
        .first()
    )

    total_rows = TrafficData.objects.count()

    context = {
        "form": form,
        "latest_upload": latest_upload,
        "total_rows": total_rows,
    }

    return render(request, "analytics/upload_raw_data.html", context)


@login_required
def generate_forecast_view(request):
    if request.method != "POST":
        return redirect("dashboard")

    try:
        from .services.forecasting import generate_all_forecasts

        forecast_days = int(request.POST.get("forecast_days", 7))

        if forecast_days < 1:
            forecast_days = 7

        if forecast_days > 30:
            forecast_days = 30

        forecast_run = ForecastRun.objects.create(
            status=ForecastRun.STATUS_RUNNING,
            forecast_days=forecast_days,
        )

        total_created = generate_all_forecasts(
            forecast_days=forecast_days,
            forecast_run=forecast_run,
        )

        forecast_run.mark_success(total_predictions=total_created)

        messages.success(
            request,
            f"Forecast berhasil dibuat. Total prediksi: {total_created} data."
        )

    except Exception as error:
        try:
            forecast_run.mark_failed(error)
        except Exception:
            pass

        messages.error(
            request,
            f"Gagal membuat forecast: {error}"
        )

    return redirect("dashboard")