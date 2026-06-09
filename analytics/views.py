import json
import re
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Max, Min, Sum
from django.shortcuts import redirect, render
from django.utils.text import slugify

from analytics.forms import CSVUploadForm
from analytics.models import Category, ForecastRun, Prediction, TrafficData
from analytics.services.csv_importer import import_raw_traffic_csv
from analytics.services.forecasting import (
    MAX_FORECAST_DAYS,
    create_forecast_run_and_generate,
    normalize_forecast_days,
)


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


def parse_views_value(value):
    try:
        views = int(float(value))
    except (TypeError, ValueError):
        return None

    if views < 0:
        return None

    return views


def format_number(value):
    try:
        return f"{int(round(float(value))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def format_metric(value, digits=1, suffix=""):
    if value in [None, ""]:
        return "Belum ada"

    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "Belum ada"


def normalize_percent_metric(value):
    if value in [None, ""]:
        return None

    try:
        metric = float(value)
    except (TypeError, ValueError):
        return None

    if 0 <= metric <= 1:
        return metric * 100

    return metric


def format_percent_metric(value, digits=2):
    metric = normalize_percent_metric(value)

    if metric is None:
        return "Belum ada"

    return f"{metric:.{digits}f}%"


def format_percent_value(value, digits=2):
    if value in [None, ""]:
        return "Belum ada"

    try:
        return f"{float(value):.{digits}f}%"
    except (TypeError, ValueError):
        return "Belum ada"


def percentage_change(current_value, previous_value):
    if previous_value in [0, None]:
        return None

    return round(((current_value - previous_value) / previous_value) * 100, 1)


def get_trend_label(change_percentage):
    if change_percentage is None:
        return "Belum cukup data"

    if change_percentage > 5:
        return "Naik"

    if change_percentage < -5:
        return "Turun"

    return "Stabil"


def get_alert_tone(change_percentage):
    if change_percentage is None:
        return "neutral"

    if change_percentage > 10:
        return "up"

    if change_percentage < -10:
        return "down"

    return "stable"


def get_alert_label(change_percentage):
    if change_percentage is None:
        return "Data kurang"

    if change_percentage > 10:
        return "Naik"

    if change_percentage < -10:
        return "Turun"

    return "Stabil"


def get_prediction_status(wmape_value, needs_more_data=False):
    if wmape_value in [None, ""]:
        return (
            "Perlu dipantau",
            "WMAPE belum tersedia, gunakan MAE/RMSE sebagai pendukung."
        )

    if needs_more_data:
        return (
            "Data terbatas",
            "Tambahkan histori traffic agar prediksi lebih stabil untuk dibaca redaksi."
        )

    try:
        wmape_value = float(wmape_value)
    except (TypeError, ValueError):
        return (
            "Perlu dipantau",
            "Data evaluasi belum cukup untuk membaca kualitas prediksi."
        )

    if wmape_value <= 15:
        return (
            "Prediksi cukup akurat",
            "Prediksi cukup akurat untuk acuan awal redaksi."
        )

    if wmape_value <= 30:
        return (
            "Prediksi cukup layak",
            "Prediksi cukup layak, tetap pantau kategori dengan perubahan besar."
        )

    if wmape_value <= 50:
        return (
            "Perlu dipantau",
            "Prediksi perlu dipantau karena error masih cukup tinggi."
        )

    return (
        "Perlu evaluasi",
        "Prediksi perlu evaluasi sebelum dijadikan acuan utama."
    )


def get_mape_status(mape_value):
    mape_value = normalize_percent_metric(mape_value)

    if mape_value is None:
        return "Belum cukup data evaluasi"

    if mape_value < 10:
        return "Prediksi cukup akurat"

    if mape_value <= 20:
        return "Prediksi cukup layak"

    return "Prediksi perlu dievaluasi"


def clean_order_label(value):
    if not value:
        return ""

    return str(value).replace(" ", "")


def is_empty_seasonal_order(value):
    return clean_order_label(value) in ["", "(0,0,0,0)", "(0,0,0,7)"]


def format_active_model(model_name, arima_order=None, seasonal_order=None):
    model_name = (model_name or "").strip()
    arima_order = clean_order_label(arima_order)
    seasonal_order = clean_order_label(seasonal_order)
    normalized_name = model_name.lower()

    if "moving" in normalized_name or "fallback" in normalized_name:
        return "Moving Average"

    if "(" in model_name and (
        normalized_name.startswith("arima") or
        normalized_name.startswith("sarima")
    ):
        return model_name.replace(" ", "")

    if seasonal_order and not is_empty_seasonal_order(seasonal_order):
        return f"SARIMA{arima_order or ''}{seasonal_order}"

    if arima_order:
        return f"ARIMA{arima_order}"

    return model_name or "ARIMA"


def get_model_field_names(model_class):
    return {field.name for field in model_class._meta.fields}


def get_latest_forecast_run():
    forecast_run_fields = get_model_field_names(ForecastRun)

    status_success = getattr(ForecastRun, "STATUS_SUCCESS", "success")
    status_partial = getattr(ForecastRun, "STATUS_PARTIAL", "partial")

    queryset = ForecastRun.objects.all()

    if "status" in forecast_run_fields:
        queryset = queryset.filter(status__in=[status_success, status_partial])

    order_fields = []

    if "finished_at" in forecast_run_fields:
        order_fields.append("-finished_at")

    if "created_at" in forecast_run_fields:
        order_fields.append("-created_at")

    if "started_at" in forecast_run_fields:
        order_fields.append("-started_at")

    if "id" in forecast_run_fields:
        order_fields.append("-id")

    if order_fields:
        queryset = queryset.order_by(*order_fields)

    return queryset.first()


def get_forecast_run_display_time(forecast_run):
    if not forecast_run:
        return "Belum ada"

    for field_name in ["finished_at", "created_at", "started_at"]:
        value = getattr(forecast_run, field_name, None)

        if value:
            return value.strftime("%d %b %Y %H:%M")

    return "Belum ada"


def get_forecast_run_total_predictions(forecast_run):
    if not forecast_run:
        return 0

    value = getattr(forecast_run, "total_predictions", 0)

    return value or 0


def get_forecast_run_status(forecast_run):
    if not forecast_run:
        return "Belum ada"

    if hasattr(forecast_run, "get_status_display"):
        try:
            return forecast_run.get_status_display()
        except Exception:
            pass

    return getattr(forecast_run, "status", "Selesai")


def get_or_create_category(category_name):
    category_fields = get_model_field_names(Category)

    existing_category = Category.objects.filter(name=category_name).first()

    if existing_category:
        return existing_category

    defaults = {}

    if "slug" in category_fields:
        base_slug = slugify(category_name) or "kategori"
        slug = base_slug[:110]
        counter = 2

        while Category.objects.filter(slug=slug).exists():
            slug = f"{base_slug[:104]}-{counter}"
            counter += 1

        defaults["slug"] = slug

    category, _ = Category.objects.get_or_create(
        name=category_name,
        defaults=defaults,
    )

    return category


def build_category_cache(category_names):
    """
    Ambil/buat kategori sekali per upload, bukan query get_or_create per row CSV.
    """
    normalized_names = sorted({
        str(category_name).strip()
        for category_name in category_names
        if str(category_name).strip()
    })

    if not normalized_names:
        return {}

    existing_categories = {
        category.name: category
        for category in Category.objects.filter(name__in=normalized_names)
    }

    missing_names = [
        category_name
        for category_name in normalized_names
        if category_name not in existing_categories
    ]

    if missing_names:
        category_fields = get_model_field_names(Category)
        existing_slugs = set(
            Category.objects
            .exclude(slug="")
            .values_list("slug", flat=True)
        )
        categories_to_create = []

        for category_name in missing_names:
            category_kwargs = {"name": category_name}

            if "slug" in category_fields:
                base_slug = (slugify(category_name) or "kategori")[:110]
                slug = base_slug
                counter = 2

                while slug in existing_slugs:
                    slug = f"{base_slug[:104]}-{counter}"
                    counter += 1

                existing_slugs.add(slug)
                category_kwargs["slug"] = slug

            categories_to_create.append(Category(**category_kwargs))

        Category.objects.bulk_create(categories_to_create, batch_size=500)

        existing_categories = {
            category.name: category
            for category in Category.objects.filter(name__in=normalized_names)
        }

    return existing_categories


@login_required
def dashboard(request):
    selected_category = request.GET.get("category", "").strip()
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    categories = Category.objects.all().order_by("name")

    traffic_queryset = TrafficData.objects.select_related("category").all()

    latest_forecast_run = get_latest_forecast_run()

    prediction_queryset = Prediction.objects.select_related("category").all()

    prediction_fields = get_model_field_names(Prediction)

    if latest_forecast_run and "forecast_run" in prediction_fields:
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

    top_actual_categories = list(
        traffic_queryset
        .values("category__name")
        .annotate(total_views=Sum("views"))
        .order_by("-total_views")[:5]
    )

    top_forecast_categories = list(
        prediction_queryset
        .values("category__name")
        .annotate(total_predicted_views=Sum("predicted_views"))
        .order_by("-total_predicted_views")[:5]
    )

    last_prediction = (
        prediction_queryset
        .select_related("category")
        .order_by("-generated_at")
        .first()
    )

    latest_7_actual_views = sum(actual_views[-7:]) if actual_views else 0
    previous_7_actual_views = sum(actual_views[-14:-7]) if len(actual_views) >= 14 else 0

    actual_trend_percentage = percentage_change(
        latest_7_actual_views,
        previous_7_actual_views,
    )

    actual_trend_label = get_trend_label(actual_trend_percentage)

    recent_actual_average = (
        round(latest_7_actual_views / min(len(actual_views), 7), 1)
        if actual_views else 0
    )

    forecast_average = (
        round(total_forecast_views / len(forecast_views), 1)
        if forecast_views else 0
    )

    comparison_days = min(len(forecast_views) or 7, len(actual_views) or 7)
    recent_actual_comparison_views = (
        sum(actual_views[-comparison_days:])
        if actual_views and comparison_days else 0
    )
    forecast_comparison_views = (
        sum(forecast_views[:comparison_days])
        if forecast_views and comparison_days else 0
    )
    recent_actual_comparison_average = (
        round(recent_actual_comparison_views / comparison_days, 1)
        if comparison_days and recent_actual_comparison_views else 0
    )
    forecast_comparison_average = (
        round(forecast_comparison_views / comparison_days, 1)
        if comparison_days and forecast_comparison_views else 0
    )
    forecast_comparison_percentage = percentage_change(
        forecast_comparison_views,
        recent_actual_comparison_views,
    )
    forecast_comparison_trend_label = get_trend_label(
        forecast_comparison_percentage
    )

    forecast_vs_recent_percentage = percentage_change(
        forecast_average,
        recent_actual_average,
    )

    forecast_trend_label = get_trend_label(forecast_vs_recent_percentage)

    top_actual_category = top_actual_categories[0] if top_actual_categories else None
    top_forecast_category = top_forecast_categories[0] if top_forecast_categories else None

    top_actual_share = 0
    top_forecast_share = 0

    if top_actual_category and total_actual_views > 0:
        top_actual_share = round(
            (top_actual_category["total_views"] / total_actual_views) * 100,
            1,
        )

    if top_forecast_category and total_forecast_views > 0:
        top_forecast_share = round(
            (top_forecast_category["total_predicted_views"] / total_forecast_views) * 100,
            1,
        )

    highest_actual_day = None

    if actual_grouped:
        highest_actual_date, highest_actual_views = max(
            actual_grouped.items(),
            key=lambda item: item[1],
        )

        highest_actual_day = {
            "date": highest_actual_date,
            "views": highest_actual_views,
        }

    confidence_width_average = 0
    confidence_status = "Belum ada forecast"

    if forecast_views and forecast_lower and forecast_upper:
        confidence_widths = []

        for index, forecast_value in enumerate(forecast_views):
            lower_value = forecast_lower[index] if index < len(forecast_lower) else 0
            upper_value = forecast_upper[index] if index < len(forecast_upper) else 0

            if forecast_value > 0:
                confidence_widths.append(
                    ((upper_value - lower_value) / forecast_value) * 100
                )

        if confidence_widths:
            confidence_width_average = round(
                sum(confidence_widths) / len(confidence_widths),
                1,
            )

            if confidence_width_average <= 35:
                confidence_status = "Prediksi cukup stabil"
            elif confidence_width_average <= 70:
                confidence_status = "Prediksi sedang"
            else:
                confidence_status = "Prediksi masih melebar"

    insight_cards = [
        {
            "icon": "📊",
            "title": "Tren Aktual 7 Hari Terakhir",
            "value": actual_trend_label,
            "description": (
                f"Traffic 7 hari terakhir berjumlah {format_number(latest_7_actual_views)} views. "
                f"Periode sebelumnya berjumlah {format_number(previous_7_actual_views)} views."
            ),
        },
        {
            "icon": "📈",
            "title": "Arah Forecast",
            "value": forecast_comparison_trend_label,
            "description": (
                f"Rata-rata prediksi adalah {format_number(forecast_comparison_average)} views/hari. "
                f"Rata-rata aktual {comparison_days} hari terakhir adalah "
                f"{format_number(recent_actual_comparison_average)} views/hari."
            ),
        },
        {
            "icon": "🏷️",
            "title": "Kategori Aktual Terkuat",
            "value": top_actual_category["category__name"] if top_actual_category else "Belum ada",
            "description": (
                f"Kategori ini menyumbang sekitar {top_actual_share}% dari total Traffic Aktual."
                if top_actual_category else
                "Belum ada kategori aktual yang bisa dianalisis."
            ),
        },
        {
            "icon": "🎯",
            "title": "Kategori Forecast Potensial",
            "value": top_forecast_category["category__name"] if top_forecast_category else "Belum ada",
            "description": (
                f"Kategori ini diprediksi menyumbang sekitar {top_forecast_share}% dari total Prediksi Traffic."
                if top_forecast_category else
                "Belum ada kategori prediksi. Jalankan Buat Prediksi terlebih dahulu."
            ),
        },
        {
            "icon": "🔥",
            "title": "Hari Traffic Tertinggi",
            "value": highest_actual_day["date"] if highest_actual_day else "Belum ada",
            "description": (
                f"Traffic tertinggi tercatat sebesar {format_number(highest_actual_day['views'])} views."
                if highest_actual_day else
                "Belum ada data aktual yang bisa dibaca."
            ),
        },
        {
            "icon": "🧭",
            "title": "Kejelasan Prediksi",
            "value": confidence_status,
            "description": (
                f"Rata-rata lebar rentang prediksi sekitar {confidence_width_average}%."
                if confidence_width_average > 0 else
                "Belum ada lower bound dan upper bound yang bisa dievaluasi."
            ),
        },
    ]

    if total_actual_views <= 0:
        insight_summary = (
            "Dashboard belum memiliki data aktual untuk dianalisis. "
            "Upload CSV terlebih dahulu agar sistem bisa menampilkan pola traffic."
        )
    elif total_forecast_views <= 0:
        insight_summary = (
            f"Data aktual sudah tersedia dengan total {format_number(total_actual_views)} views. "
            "Prediksi belum tersedia, jadi klik Buat Prediksi untuk melihat arah traffic ke depan."
        )
    else:
        change_text = "belum bisa dibandingkan"
        if forecast_comparison_percentage is not None:
            change_text = (
                f"{forecast_comparison_trend_label.lower()} sekitar "
                f"{abs(forecast_comparison_percentage)}%"
            )

        insight_summary = (
            f"Prediksi {comparison_days} hari ke depan menunjukkan estimasi traffic sekitar "
            f"{format_number(forecast_comparison_views)} views. Dibandingkan "
            f"{comparison_days} hari terakhir ({format_number(recent_actual_comparison_views)} views), "
            f"traffic diperkirakan {change_text}. Redaksi dapat memantau kategori utama "
            "dan menyiapkan konten pendukung. Kategori prediksi paling potensial: "
            f"{top_forecast_category['category__name'] if top_forecast_category else 'belum tersedia'}."
        )

    top_actual_labels = [
        item["category__name"]
        for item in top_actual_categories
    ]

    top_actual_values = [
        item["total_views"]
        for item in top_actual_categories
    ]

    top_forecast_labels = [
        item["category__name"]
        for item in top_forecast_categories
    ]

    top_forecast_values = [
        item["total_predicted_views"]
        for item in top_forecast_categories
    ]

    category_share_labels = top_actual_labels.copy()
    category_share_values = top_actual_values.copy()

    other_actual_views = total_actual_views - sum(category_share_values)

    if other_actual_views > 0:
        category_share_labels.append("Kategori Lainnya")
        category_share_values.append(other_actual_views)

    traffic_dates = traffic_queryset.aggregate(
        first_date=Min("date"),
        last_date=Max("date"),
        total_rows=Count("id"),
        categories_with_data=Count("category", distinct=True),
    )

    data_first_date = traffic_dates["first_date"]
    data_last_date = traffic_dates["last_date"]
    data_total_rows = traffic_dates["total_rows"] or 0
    data_categories_with_data = traffic_dates["categories_with_data"] or 0
    data_zero_view_rows = traffic_queryset.filter(views=0).count()
    data_days_covered = 0

    if data_first_date and data_last_date:
        data_days_covered = (data_last_date - data_first_date).days + 1

    data_quality_status = "Belum ada data"
    data_quality_note = "Upload CSV traffic agar kualitas data bisa dibaca."

    if data_total_rows > 0:
        if data_days_covered >= 30 and data_categories_with_data >= 3:
            data_quality_status = "Cukup kuat"
            data_quality_note = (
                "Rentang data sudah memadai untuk membaca pola kategori utama."
            )
        elif data_days_covered >= 10:
            data_quality_status = "Perlu dipantau"
            data_quality_note = (
                "Data sudah bisa dipakai, tetapi forecast akan lebih stabil dengan histori lebih panjang."
            )
        else:
            data_quality_status = "Masih tipis"
            data_quality_note = (
                "Histori masih pendek. Tambahkan data harian agar prediksi tidak terlalu rapuh."
            )

    actual_by_category_date = {}

    for item in traffic_queryset.values("category__name", "date", "views").order_by("date"):
        category_name = item["category__name"]
        actual_by_category_date.setdefault(category_name, {})
        actual_by_category_date[category_name][item["date"]] = (
            actual_by_category_date[category_name].get(item["date"], 0) +
            item["views"]
        )

    actual_by_category = {
        category_name: [
            views
            for _, views in sorted(date_map.items())
        ]
        for category_name, date_map in actual_by_category_date.items()
    }

    forecast_category_rows = (
        prediction_queryset
        .values("category__name")
        .annotate(
            total_predicted_views=Sum("predicted_views"),
            forecast_points=Count("id"),
        )
        .order_by("-total_predicted_views")
    )

    forecast_category_metrics = []

    for item in forecast_category_rows:
        category_name = item["category__name"]
        forecast_points = item["forecast_points"] or 1
        forecast_average_per_day = (
            (item["total_predicted_views"] or 0) / forecast_points
        )
        recent_values = actual_by_category.get(category_name, [])[-7:]
        recent_average = (
            sum(recent_values) / len(recent_values)
            if recent_values else 0
        )

        forecast_category_metrics.append({
            "category_name": category_name,
            "forecast_average_per_day": forecast_average_per_day,
            "recent_average": recent_average,
            "total_predicted_views": item["total_predicted_views"] or 0,
        })

    forecast_category_count = (
        prediction_queryset
        .values("category_id")
        .distinct()
        .count()
    )

    forecast_model_names = list(
        prediction_queryset
        .values_list("model_name", flat=True)
        .distinct()
        .order_by("model_name")
    )

    forecast_metrics = prediction_queryset.aggregate(
        avg_mae=Avg("mae"),
        avg_rmse=Avg("rmse"),
        avg_mape=Avg("mape"),
        avg_wmape=Avg("wmape"),
        avg_aic=Avg("aic"),
        avg_bic=Avg("bic"),
    )

    best_model_metric = (
        prediction_queryset
        .exclude(wmape__isnull=True)
        .values("model_name", "arima_order", "seasonal_order", "wmape", "mape", "mae", "rmse", "aic", "bic")
        .order_by("wmape", "mae", "aic")
        .first()
    )

    best_model_display = "Belum ada"
    fallback_note = ""

    if best_model_metric:
        best_model_display = format_active_model(
            best_model_metric.get("model_name"),
            best_model_metric.get("arima_order"),
            best_model_metric.get("seasonal_order"),
        )

    if any(
        "moving" in (model_name or "").lower() or "fallback" in (model_name or "").lower()
        for model_name in forecast_model_names
    ):
        fallback_note = (
            "Fallback: Moving Average digunakan untuk kategori dengan data kurang stabil."
        )

    dominant_model_row = (
        prediction_queryset
        .values("model_name", "arima_order", "seasonal_order")
        .annotate(total=Count("id"))
        .order_by("-total", "model_name")
        .first()
    )
    dominant_model_display = "Belum ada"

    if dominant_model_row:
        dominant_model_display = format_active_model(
            dominant_model_row.get("model_name"),
            dominant_model_row.get("arima_order"),
            dominant_model_row.get("seasonal_order"),
        )

    wmape_denominator = sum(
        item["recent_average"]
        for item in forecast_category_metrics
        if item["recent_average"] > 0
    )
    wmape_numerator = sum(
        abs(item["recent_average"] - item["forecast_average_per_day"])
        for item in forecast_category_metrics
        if item["recent_average"] > 0
    )
    wmape_value = (
        round((wmape_numerator / wmape_denominator) * 100, 2)
        if wmape_denominator > 0 else None
    )

    smape_terms = []

    for item in forecast_category_metrics:
        denominator = (
            abs(item["recent_average"]) +
            abs(item["forecast_average_per_day"])
        ) / 2

        if denominator > 0:
            smape_terms.append(
                abs(item["recent_average"] - item["forecast_average_per_day"]) /
                denominator
            )

    smape_value = (
        round((sum(smape_terms) / len(smape_terms)) * 100, 2)
        if smape_terms else None
    )

    fallback_category_ids = set()

    for item in prediction_queryset.values("category_id", "model_name"):
        model_name = (item["model_name"] or "").lower()

        if "moving" in model_name or "fallback" in model_name:
            fallback_category_ids.add(item["category_id"])

    fallback_category_count = len(fallback_category_ids)
    fallback_dominant = (
        forecast_category_count > 0 and
        fallback_category_count / forecast_category_count >= 0.5
    )
    needs_more_prediction_data = (
        data_days_covered < 10 or
        (fallback_dominant and data_days_covered < 60)
    )

    model_wmape_value = forecast_metrics["avg_wmape"] or wmape_value

    prediction_status, prediction_status_detail = get_prediction_status(
        model_wmape_value,
        needs_more_data=needs_more_prediction_data,
    )

    if fallback_dominant and data_days_covered < 60:
        prediction_status_detail = (
            "Perlu data tambahan karena cukup banyak kategori memakai Moving Average."
        )
    elif fallback_dominant:
        prediction_status_detail = (
            f"{prediction_status_detail} ARIMA tetap digunakan untuk kategori yang stabil; "
            "Moving Average hanya dipakai sebagai fallback pada kategori berpola rendah atau tidak stabil."
        )

    mape_status = get_mape_status(forecast_metrics["avg_mape"])

    forecast_quality_items = [
        {
            "label": "Status Prediksi",
            "value": prediction_status,
            "detail": prediction_status_detail,
            "tooltip": "Status utama dihitung dari WMAPE dan kondisi kecukupan data.",
        },
        {
            "label": "WMAPE",
            "value": format_percent_metric(forecast_metrics["avg_wmape"]),
            "detail": "Error berbobot terhadap total traffic, lebih stabil untuk data traffic kecil atau 0.",
            "tooltip": "WMAPE = total selisih absolut dibagi total traffic aktual pada data uji.",
        },
        {
            "label": "Rata-rata lebar rentang prediksi",
            "value": (
                f"{confidence_width_average}%"
                if confidence_width_average else
                "Belum ada"
            ),
            "detail": (
                "Semakin kecil nilainya, semakin rapat rentang prediksi dan semakin stabil hasil forecast."
            ),
            "tooltip": "Dihitung dari jarak Batas Bawah dan Batas Atas terhadap nilai prediksi.",
        },
        {
            "label": "Cakupan kategori",
            "value": f"{forecast_category_count}/{data_categories_with_data}",
            "detail": "Kategori dengan data aktual yang ikut memiliki prediksi.",
            "tooltip": "Jumlah kategori yang punya hasil prediksi dibanding kategori aktif di data aktual.",
        },
        {
            "label": "Model dominan",
            "value": dominant_model_display,
            "detail": (
                "Model yang paling banyak dipakai pada run prediksi terbaru."
            ),
            "tooltip": "ARIMA tetap menjadi model utama saat data kategori layak.",
        },
    ]

    forecast_technical_items = [
        {
            "label": "MAPE",
            "value": format_percent_metric(forecast_metrics["avg_mape"]),
            "detail": (
                f"{mape_status}. Error persentase rata-rata. "
                "Sensitif pada kategori dengan views kecil."
            ),
            "tooltip": "MAPE tetap ditampilkan sebagai detail teknis, bukan penentu status utama.",
        },
        {
            "label": "SMAPE",
            "value": format_percent_value(smape_value),
            "detail": "Error persentase simetris yang lebih stabil untuk data kecil.",
            "tooltip": "SMAPE membandingkan selisih dengan rata-rata nilai aktual dan prediksi.",
        },
        {
            "label": "MAE",
            "value": format_metric(forecast_metrics["avg_mae"]),
            "detail": "Rata-rata selisih absolut antara prediksi dan data uji.",
            "tooltip": "MAE menunjukkan besar error rata-rata dalam satuan views.",
        },
        {
            "label": "RMSE",
            "value": format_metric(forecast_metrics["avg_rmse"]),
            "detail": "Akar rata-rata error kuadrat pada data uji.",
            "tooltip": "RMSE memberi penalti lebih besar pada error yang besar.",
        },
        {
            "label": "AIC / BIC",
            "value": (
                f"{format_metric(forecast_metrics['avg_aic'])} / "
                f"{format_metric(forecast_metrics['avg_bic'])}"
            ),
            "detail": "Skor pembanding model; lebih kecil biasanya lebih baik.",
            "tooltip": "AIC dan BIC membantu membandingkan model statistik. Nilai lebih kecil biasanya lebih baik.",
        },
        {
            "label": "Model aktif",
            "value": best_model_display,
            "detail": (
                "Beberapa kategori memakai Moving Average karena pola data belum cukup stabil untuk ARIMA."
                if fallback_note else
                "Model terbaik dipilih dari evaluasi train/test."
            ),
            "tooltip": "Format ARIMA(p,d,q) atau SARIMA(p,d,q)(P,D,Q,7).",
        },
    ]

    forecast_alerts = []

    for item in forecast_category_metrics:
        category_name = item["category_name"]
        forecast_average_per_day = item["forecast_average_per_day"]
        recent_average = item["recent_average"]
        change_percentage = percentage_change(
            forecast_average_per_day,
            recent_average,
        )

        forecast_alerts.append({
            "category_name": category_name,
            "label": get_alert_label(change_percentage),
            "tone": get_alert_tone(change_percentage),
            "change_percentage": change_percentage,
            "change_display": (
                f"{change_percentage}%"
                if change_percentage is not None else
                ""
            ),
            "forecast_average": round(forecast_average_per_day, 1),
            "recent_average": round(recent_average, 1),
            "total_predicted_views": item["total_predicted_views"],
        })

    category_alerts = forecast_alerts[:8]

    upward_alerts = [
        item for item in forecast_alerts
        if item["tone"] == "up"
    ][:3]

    downward_alerts = [
        item for item in forecast_alerts
        if item["tone"] == "down"
    ][:3]

    editorial_recommendations = []

    for item in upward_alerts:
        editorial_recommendations.append({
            "title": f"Dorong liputan {item['category_name']}",
            "description": (
                f"Prediksi naik {item['change_percentage']}% dari rata-rata aktual terbaru. "
                "Siapkan angle lanjutan, update cepat, dan distribusi sosial lebih awal."
            ),
        })

    for item in downward_alerts:
        editorial_recommendations.append({
            "title": f"Siapkan booster untuk {item['category_name']}",
            "description": (
                f"Prediksi turun {abs(item['change_percentage'])}% dari rata-rata aktual terbaru. "
                "Pertimbangkan artikel evergreen, rangkuman, atau konteks tambahan."
            ),
        })

    if not editorial_recommendations and top_forecast_category:
        editorial_recommendations.append({
            "title": f"Prioritaskan {top_forecast_category['category__name']}",
            "description": (
                "Kategori ini punya Estimasi Traffic tertinggi. Jadikan sebagai slot utama "
                "untuk agenda editorial periode prediksi."
            ),
        })

    if not editorial_recommendations:
        editorial_recommendations.append({
            "title": "Jalankan forecast untuk rekomendasi",
            "description": (
                "Rekomendasi aksi redaksi akan muncul setelah prediksi kategori tersedia."
            ),
        })

    forecast_history = ForecastRun.objects.all().order_by("-started_at")[:5]

    predictions_queryset = (
        prediction_queryset
        .select_related("category")
        .order_by("prediction_date", "category__name")
    )

    prediction_rows = []

    for prediction in predictions_queryset[:50]:
        category_name = prediction.category.name
        recent_values = actual_by_category.get(category_name, [])[-7:]
        recent_average = (
            sum(recent_values) / len(recent_values)
            if recent_values else 0
        )
        change_percentage = percentage_change(
            prediction.predicted_views,
            recent_average,
        )

        prediction_rows.append({
            "prediction": prediction,
            "status_label": get_alert_label(change_percentage),
            "status_tone": get_alert_tone(change_percentage),
            "change_display": (
                f"{change_percentage}%"
                if change_percentage is not None else
                "-"
            ),
        })

    is_filter_active = bool(selected_category or start_date or end_date)

    context = {
        "categories": categories,
        "selected_category": selected_category,
        "selected_start_date": start_date,
        "selected_end_date": end_date,
        "is_filter_active": is_filter_active,
        "forecast_days": 7,
        "max_forecast_days": MAX_FORECAST_DAYS,

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
        "latest_forecast_time": get_forecast_run_display_time(latest_forecast_run),
        "latest_forecast_status": get_forecast_run_status(latest_forecast_run),
        "latest_forecast_total_predictions": get_forecast_run_total_predictions(latest_forecast_run),
        "last_prediction": last_prediction,
        "prediction_rows": prediction_rows,
        "forecast_history": forecast_history,

        "insight_cards": insight_cards,
        "insight_summary": insight_summary,
        "forecast_quality_items": forecast_quality_items,
        "forecast_technical_items": forecast_technical_items,
        "category_alerts": category_alerts,
        "editorial_recommendations": editorial_recommendations,
        "data_quality_status": data_quality_status,
        "data_quality_note": data_quality_note,
        "data_first_date": data_first_date,
        "data_last_date": data_last_date,
        "data_days_covered": data_days_covered,
        "data_total_rows": data_total_rows,
        "data_zero_view_rows": data_zero_view_rows,
        "data_categories_with_data": data_categories_with_data,

        "top_actual_labels": json.dumps(top_actual_labels),
        "top_actual_values": json.dumps(top_actual_values),
        "top_forecast_labels": json.dumps(top_forecast_labels),
        "top_forecast_values": json.dumps(top_forecast_values),
        "category_share_labels": json.dumps(category_share_labels),
        "category_share_values": json.dumps(category_share_values),
        "balanced_insight": json.dumps({
            "comparisonDays": comparison_days,
            "recentActualViews": recent_actual_comparison_views,
            "forecastViews": forecast_comparison_views,
            "changePercentage": forecast_comparison_percentage,
            "trendLabel": forecast_comparison_trend_label,
            "topForecastCategory": (
                top_forecast_category["category__name"]
                if top_forecast_category else ""
            ),
            "summary": insight_summary,
        }),
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
                result = import_raw_traffic_csv(csv_file)

                if result.processed_rows == 0:
                    messages.error(
                        request,
                        "File CSV kosong. Tidak ada data yang bisa diimport."
                    )
                    return redirect("upload_raw_data")

                if result.valid_rows == 0:
                    messages.error(
                        request,
                        "Tidak ada data valid yang berhasil diproses dari CSV."
                    )
                    return redirect("upload_raw_data")

                if result.created_count == 0:
                    messages.warning(
                        request,
                        (
                            "Tidak ada data baru yang disimpan. "
                            f"{result.duplicate_in_database_count} data terdeteksi sudah ada di database."
                        ),
                    )
                    return redirect("upload_raw_data")

                messages.success(
                    request,
                    (
                        f"Import berhasil. {result.created_count} data baru disimpan. "
                        f"{result.processed_rows} row diproses. "
                        f"Periode {result.first_date} sampai {result.last_date}. "
                        f"Total kategori: {result.total_categories}."
                    ),
                )

                if result.duplicate_in_database_count > 0:
                    messages.warning(
                        request,
                        (
                            f"{result.duplicate_in_database_count} data duplikat dilewati "
                            "karena sudah ada di database."
                        ),
                    )

                if result.duplicate_in_file_count > 0:
                    messages.info(
                        request,
                        (
                            f"{result.duplicate_in_file_count} baris duplikat di file CSV "
                            "digabung berdasarkan tanggal, kategori, dan page path."
                        ),
                    )

                if result.skipped_count > 0:
                    messages.warning(
                        request,
                        (
                            f"{result.skipped_count} baris dilewati karena tanggal/views tidak valid, "
                            "homepage, halaman arsip, halaman informasi, atau noise teknis."
                        ),
                    )

                return redirect("upload_raw_data")

            except Exception as error:
                messages.error(
                    request,
                    f"Gagal memproses CSV: {error}"
                )
                return redirect("upload_raw_data")

    traffic_fields = get_model_field_names(TrafficData)

    if "created_at" in traffic_fields:
        latest_upload = (
            TrafficData.objects
            .select_related("category")
            .order_by("-created_at")
            .first()
        )
    else:
        latest_upload = (
            TrafficData.objects
            .select_related("category")
            .order_by("-id")
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

    if not TrafficData.objects.exists():
        messages.error(
            request,
            "Data traffic belum tersedia. Upload CSV terlebih dahulu sebelum generate forecast."
        )
        return redirect("dashboard")

    requested_days_raw = request.POST.get("forecast_days", 7)
    forecast_days = normalize_forecast_days(requested_days_raw)

    try:
        requested_days = int(requested_days_raw)
    except (TypeError, ValueError):
        requested_days = forecast_days

    if requested_days > MAX_FORECAST_DAYS:
        messages.warning(
            request,
            "Forecast days dibatasi maksimal 14 hari agar prediksi tetap realistis."
        )

    try:
        forecast_run = create_forecast_run_and_generate(
            forecast_days=forecast_days
        )

        total_predictions = getattr(forecast_run, "total_predictions", 0) or 0
        run_summary = getattr(forecast_run, "summary", None)
        fallback_count = getattr(run_summary, "fallback_categories", 0)
        failed_count = len(getattr(run_summary, "failed_categories", []) or [])
        success_count = getattr(run_summary, "successful_categories", 0)

        if total_predictions > 0:
            messages.success(
                request,
                (
                    "Forecast selesai. "
                    f"{success_count} kategori berhasil, "
                    f"{fallback_count} kategori fallback, "
                    f"{failed_count} kategori gagal. "
                    f"Periode prediksi: {forecast_days} hari. "
                    f"Total prediksi: {total_predictions}."
                ),
            )
        else:
            messages.warning(
                request,
                (
                    "Forecast selesai, tetapi belum ada prediksi yang tersimpan. "
                    "Cek jumlah data historis per kategori."
                ),
            )

    except Exception as error:
        messages.error(
            request,
            f"Gagal membuat forecast: {error}"
        )

    return redirect("dashboard")
