import json
import re
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils.text import slugify

from analytics.forms import CSVUploadForm
from analytics.models import Category, ForecastRun, Prediction, TrafficData
from analytics.services.forecasting import create_forecast_run_and_generate


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


def get_model_field_names(model_class):
    return {field.name for field in model_class._meta.fields}


def get_latest_forecast_run():
    forecast_run_fields = get_model_field_names(ForecastRun)

    status_success = getattr(ForecastRun, "STATUS_SUCCESS", "success")

    queryset = ForecastRun.objects.all()

    if "status" in forecast_run_fields:
        queryset = queryset.filter(status=status_success)

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
            "value": forecast_trend_label,
            "description": (
                f"Rata-rata forecast adalah {format_number(forecast_average)} views/hari. "
                f"Rata-rata aktual terbaru adalah {format_number(recent_actual_average)} views/hari."
            ),
        },
        {
            "icon": "🏷️",
            "title": "Kategori Aktual Terkuat",
            "value": top_actual_category["category__name"] if top_actual_category else "Belum ada",
            "description": (
                f"Kategori ini menyumbang sekitar {top_actual_share}% dari total actual views."
                if top_actual_category else
                "Belum ada kategori aktual yang bisa dianalisis."
            ),
        },
        {
            "icon": "🎯",
            "title": "Kategori Forecast Potensial",
            "value": top_forecast_category["category__name"] if top_forecast_category else "Belum ada",
            "description": (
                f"Kategori ini diprediksi menyumbang sekitar {top_forecast_share}% dari total forecast views."
                if top_forecast_category else
                "Belum ada kategori forecast. Jalankan Generate Forecast terlebih dahulu."
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
                f"Rata-rata rentang confidence forecast sekitar {confidence_width_average}%."
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
            "Forecast belum tersedia, jadi klik Generate Forecast untuk melihat arah prediksi."
        )
    else:
        insight_summary = (
            f"Traffic aktual berjumlah {format_number(total_actual_views)} views, "
            f"sedangkan hasil forecast memperkirakan {format_number(total_forecast_views)} views. "
            f"Tren aktual saat ini: {actual_trend_label}. "
            f"Kategori forecast paling potensial: "
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
        "latest_forecast_time": get_forecast_run_display_time(latest_forecast_run),
        "latest_forecast_status": get_forecast_run_status(latest_forecast_run),
        "latest_forecast_total_predictions": get_forecast_run_total_predictions(latest_forecast_run),
        "last_prediction": last_prediction,
        "predictions": predictions,

        "insight_cards": insight_cards,
        "insight_summary": insight_summary,

        "top_actual_labels": json.dumps(top_actual_labels),
        "top_actual_values": json.dumps(top_actual_values),
        "top_forecast_labels": json.dumps(top_forecast_labels),
        "top_forecast_values": json.dumps(top_forecast_values),
        "category_share_labels": json.dumps(category_share_labels),
        "category_share_values": json.dumps(category_share_values),
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
                valid_row_count = 0
                traffic_map = {}

                for _, row in df.iterrows():
                    traffic_date = parse_date_value(row.get(date_column))
                    page_path = clean_page_path(row.get(path_column))
                    views = parse_views_value(row.get(views_column, 0))

                    if not traffic_date or views is None:
                        skipped_count += 1
                        continue

                    category_name = detect_category_from_path(page_path)

                    if category_name in EXCLUDED_FORECAST_CATEGORIES:
                        skipped_count += 1
                        continue

                    category = get_or_create_category(category_name)

                    key = (
                        category.id,
                        traffic_date,
                        page_path,
                    )

                    if key not in traffic_map:
                        traffic_map[key] = {
                            "category": category,
                            "date": traffic_date,
                            "page_path": page_path,
                            "views": 0,
                        }

                    traffic_map[key]["views"] += views
                    valid_row_count += 1

                if not traffic_map:
                    messages.error(
                        request,
                        "Tidak ada data valid yang berhasil diproses dari CSV."
                    )
                    return redirect("upload_raw_data")

                category_ids = list({
                    item["category"].id
                    for item in traffic_map.values()
                })

                dates = list({
                    item["date"]
                    for item in traffic_map.values()
                })

                page_paths = list({
                    item["page_path"]
                    for item in traffic_map.values()
                })

                existing_keys = set(
                    TrafficData.objects
                    .filter(
                        category_id__in=category_ids,
                        date__in=dates,
                        page_path__in=page_paths,
                    )
                    .values_list("category_id", "date", "page_path")
                )

                traffic_objects = []

                for key, item in traffic_map.items():
                    if key in existing_keys:
                        continue

                    traffic_objects.append(
                        TrafficData(
                            category=item["category"],
                            date=item["date"],
                            page_path=item["page_path"],
                            views=item["views"],
                        )
                    )

                duplicate_in_file_count = valid_row_count - len(traffic_map)
                duplicate_in_database_count = len(traffic_map) - len(traffic_objects)

                if not traffic_objects:
                    messages.warning(
                        request,
                        (
                            "Tidak ada data baru yang disimpan. "
                            f"{duplicate_in_database_count} data terdeteksi sudah ada di database."
                        ),
                    )
                    return redirect("upload_raw_data")

                TrafficData.objects.bulk_create(
                    traffic_objects,
                    batch_size=1000,
                )

                created_count = len(traffic_objects)
                first_date = min(item.date for item in traffic_objects)
                last_date = max(item.date for item in traffic_objects)
                total_categories = Category.objects.count()

                messages.success(
                    request,
                    (
                        f"Import berhasil. {created_count} data baru disimpan. "
                        f"Periode {first_date} sampai {last_date}. "
                        f"Total kategori: {total_categories}."
                    ),
                )

                if duplicate_in_database_count > 0:
                    messages.warning(
                        request,
                        (
                            f"{duplicate_in_database_count} data duplikat dilewati "
                            "karena sudah ada di database."
                        ),
                    )

                if duplicate_in_file_count > 0:
                    messages.info(
                        request,
                        (
                            f"{duplicate_in_file_count} baris duplikat di file CSV "
                            "digabung berdasarkan tanggal, kategori, dan page path."
                        ),
                    )

                if skipped_count > 0:
                    messages.warning(
                        request,
                        (
                            f"{skipped_count} baris dilewati karena tanggal/views tidak valid, "
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

    forecast_days = request.POST.get("forecast_days", 7)

    try:
        forecast_days = int(forecast_days)
    except (TypeError, ValueError):
        forecast_days = 7

    forecast_days = max(1, min(forecast_days, 30))

    try:
        forecast_run = create_forecast_run_and_generate(
            forecast_days=forecast_days
        )

        total_predictions = getattr(forecast_run, "total_predictions", 0) or 0

        if total_predictions > 0:
            messages.success(
                request,
                (
                    f"Forecast berhasil dibuat untuk {forecast_days} hari ke depan. "
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
