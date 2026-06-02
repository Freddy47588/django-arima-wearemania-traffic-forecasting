import json
import re
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect

from analytics.forms import CSVUploadForm
from analytics.models import Category, TrafficData, Prediction, ForecastRun
from analytics.services.forecasting import generate_all_forecasts


EXCLUDED_FORECAST_CATEGORIES = [
    "Homepage",
    "Halaman Arsip",
    "Halaman Informasi",
    "Noise / Teknis",
]


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
    """
    Membersihkan page path dari CSV/GA4 agar format URL konsisten.
    Contoh:
    https://wearemania.net/berita-arema/contoh?utm=abc
    menjadi:
    /berita-arema/contoh
    """

    if pd.isna(page_path):
        return "/"

    page_path = str(page_path).strip()

    if not page_path or page_path.lower() in ["nan", "null", "(other)", "other"]:
        return "/"

    if page_path.startswith("http://") or page_path.startswith("https://"):
        try:
            parsed_url = urlparse(page_path)
            page_path = parsed_url.path or "/"
        except Exception:
            pass

    page_path = page_path.split("?")[0].split("#")[0]

    if not page_path.startswith("/"):
        page_path = f"/{page_path}"

    page_path = re.sub(r"/+", "/", page_path)
    page_path = page_path.lower().strip()

    if len(page_path) > 1:
        page_path = page_path.rstrip("/")

    return page_path


def detect_category_from_path(page_path):
    """
    Mapping URL path Wearemania ke kategori berita.
    """

    path = clean_page_path(page_path)

    if path in ["/", ""]:
        return "Homepage"

    if any(keyword in path for keyword in [
        "/tag",
        "/category",
        "/author",
        "/date",
        "/page",
        "/search",
    ]):
        return "Halaman Arsip"

    if any(keyword in path for keyword in [
        "/iklan",
        "/disclaimer",
        "/pedoman-media-online",
        "/kebijakan-privasi",
        "/kontak",
        "/contact",
        "/redaksi-wearemania",
        "/sponsor",
        "/ratecard",
        "/about",
        "/tentang-kami",
    ]):
        return "Halaman Informasi"

    if any(keyword in path for keyword in [
        "/wp-content",
        "/wp-admin",
        "/wp-json",
        "/.well-known",
        "wpac-",
        "xnyc-",
        "sackboy",
        "panderma",
        "/resource",
        "/lander",
        "/feed",
        "/xmlrpc",
        "/robots.txt",
        "/favicon",
    ]):
        return "Noise / Teknis"

    category_rules = {
        "Berita Arema": [
            "/berita-arema",
            "/arema-news",
            "/arema-fc",
            "/news/",
        ],
        "Aremaday": [
            "/aremaday",
            "/arema-day",
        ],
        "Aremania": [
            "/aremania",
            "/aremania-voice",
        ],
        "Fokus / Analisis": [
            "/fokus",
            "/ruang-taktik",
            "/analisis",
            "/opini",
        ],
        "Nasional": [
            "/nasional",
        ],
        "Ngalam / Malang Raya": [
            "/ngalam",
            "/malang-raya",
        ],
        "Futsal": [
            "/liga-futsal-profesional-indonesia",
            "/usc-futsal-league",
            "/futsal",
        ],
        "Arema Putri": [
            "/arema-putri",
        ],
        "Arema Junior": [
            "/arema-junior",
            "/akademi-arema",
        ],
        "Sejarah Arema": [
            "/memori-arema",
            "/legenda",
            "/this-day-in-history",
            "/sejarah",
            "sejarah-arema-hari-ini",
            "sejarah-hari-ini",
        ],
        "Intip Lawan": [
            "/intip-lawan",
        ],
        "Bursa Transfer": [
            "/bursa-transfer-pemain",
            "/bursa-transfer",
            "/transfer",
        ],
        "Jadwal, Hasil & Klasemen": [
            "/jadwal-hasil",
            "/pertandingan",
            "/jadwal_skor",
            "/jadwal",
            "/hasil",
            "/klasemen",
            "/posisi",
            "/kick-off",
            "/susunan-pemain",
            "/live_commentary",
        ],
        "Profil Pemain & Staff": [
            "/pemain",
            "/player",
            "/staff",
            "/pelatih",
            "/official",
        ],
        "Foto & Video": [
            "/lensa",
            "/berita-foto",
            "/photoplayer",
            "/topshot",
            "/wallpaper",
            "/video",
        ],
        "Review Jersey": [
            "/review-jersey",
            "/jersey",
        ],
        "Kompetisi": [
            "/kompetisi",
        ],
        "E-Football": [
            "/indonesian-football-e-league",
            "/e-football",
        ],
        "Luar Lapangan": [
            "/luar-lapangan",
        ],
        "Profil Klub / Kompetisi": [
            "/klub",
            "/venue",
            "/stadion",
            "/musim",
            "/liga",
            "/arema/",
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
        "%b %d, %Y",
        "%B %d, %Y",
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
    selected_category = request.GET.get("category", "").strip()
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    categories = Category.objects.all().order_by("name")

    traffic_queryset = TrafficData.objects.select_related("category").all()

    success_status = getattr(ForecastRun, "STATUS_SUCCESS", "success")

    latest_forecast_run = (
        ForecastRun.objects
        .filter(status=success_status)
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

    if start_date:
        try:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            traffic_queryset = traffic_queryset.filter(date__gte=parsed_start_date)
            prediction_queryset = prediction_queryset.filter(
                prediction_date__gte=parsed_start_date
            )
        except ValueError:
            messages.warning(
                request,
                "Format tanggal awal tidak valid. Gunakan format YYYY-MM-DD."
            )
            start_date = ""

    if end_date:
        try:
            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            traffic_queryset = traffic_queryset.filter(date__lte=parsed_end_date)
            prediction_queryset = prediction_queryset.filter(
                prediction_date__lte=parsed_end_date
            )
        except ValueError:
            messages.warning(
                request,
                "Format tanggal akhir tidak valid. Gunakan format YYYY-MM-DD."
            )
            end_date = ""

    actual_grouped = {}

    for item in traffic_queryset.values("date", "views").order_by("date"):
        date_str = item["date"].strftime("%Y-%m-%d")
        actual_grouped[date_str] = actual_grouped.get(date_str, 0) + item["views"]

    actual_labels = list(actual_grouped.keys())
    actual_views = list(actual_grouped.values())

    forecast_grouped = {}
    forecast_lower_grouped = {}
    forecast_upper_grouped = {}

    for item in prediction_queryset.values(
        "prediction_date",
        "predicted_views",
        "lower_bound",
        "upper_bound",
    ).order_by("prediction_date"):
        date_str = item["prediction_date"].strftime("%Y-%m-%d")

        forecast_grouped[date_str] = (
            forecast_grouped.get(date_str, 0) + item["predicted_views"]
        )

        lower_value = item.get("lower_bound") or 0
        upper_value = item.get("upper_bound") or 0

        forecast_lower_grouped[date_str] = (
            forecast_lower_grouped.get(date_str, 0) + lower_value
        )

        forecast_upper_grouped[date_str] = (
            forecast_upper_grouped.get(date_str, 0) + upper_value
        )

    forecast_labels = list(forecast_grouped.keys())
    forecast_views = list(forecast_grouped.values())
    forecast_lower = [forecast_lower_grouped.get(label, 0) for label in forecast_labels]
    forecast_upper = [forecast_upper_grouped.get(label, 0) for label in forecast_labels]

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

    predictions = (
        prediction_queryset
        .select_related("category")
        .order_by("prediction_date", "category__name")[:20]
    )

    is_filter_active = bool(selected_category or start_date or end_date)

    context = {
        "categories": categories,
        "selected_category": selected_category,
        "selected_start_date": start_date,
        "selected_end_date": end_date,
        "is_filter_active": is_filter_active,

        "actual_labels": json.dumps(actual_labels),
        "actual_views": json.dumps(actual_views),
        "forecast_labels": json.dumps(forecast_labels),
        "forecast_views": json.dumps(forecast_views),
        "forecast_lower": json.dumps(forecast_lower),
        "forecast_upper": json.dumps(forecast_upper),

        "total_actual_views": total_actual_views,
        "total_forecast_views": total_forecast_views,
        "total_categories": total_categories,
        "total_traffic_data": total_traffic_data,

        "top_actual_categories": top_actual_categories,
        "top_forecast_categories": top_forecast_categories,

        "latest_forecast_run": latest_forecast_run,
        "last_prediction": last_prediction,
        "predictions": predictions,
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
                    messages.error(
                        request,
                        "File CSV kosong. Tidak ada data yang bisa diimport."
                    )
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

                    if category_name in EXCLUDED_FORECAST_CATEGORIES:
                        skipped_count += 1
                        continue

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
                        f"{skipped_count} baris dilewati karena tanggal/views tidak valid, halaman arsip, halaman informasi, homepage, atau noise teknis."
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

    forecast_days = request.POST.get("forecast_days", 7)

    try:
        forecast_days = int(forecast_days)
    except (TypeError, ValueError):
        forecast_days = 7

    forecast_days = max(1, min(forecast_days, 30))

    try:
        total_predictions = generate_all_forecasts(forecast_days=forecast_days)

        messages.success(
            request,
            f"Forecast berhasil dibuat untuk {forecast_days} hari ke depan. "
            f"Total prediksi: {total_predictions}"
        )

    except Exception as error:
        messages.error(
            request,
            f"Gagal membuat forecast: {error}"
        )

    return redirect("dashboard")