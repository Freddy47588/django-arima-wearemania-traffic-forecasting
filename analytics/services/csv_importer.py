import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from analytics.models import Category, TrafficData


BATCH_SIZE = 500
CSV_CHUNK_SIZE = 1000

EXCLUDED_FORECAST_CATEGORIES = [
    "Homepage",
    "Halaman Arsip",
    "Halaman Informasi",
    "Noise / Teknis",
]


@dataclass
class ImportResult:
    processed_rows: int = 0
    valid_rows: int = 0
    created_count: int = 0
    duplicate_in_file_count: int = 0
    duplicate_in_database_count: int = 0
    skipped_count: int = 0
    first_date: object = None
    last_date: object = None
    total_categories: int = 0


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


def build_category_cache(category_names):
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
        existing_slugs = set(
            Category.objects
            .exclude(slug="")
            .values_list("slug", flat=True)
        )
        categories_to_create = []

        for category_name in missing_names:
            base_slug = (slugify(category_name) or "kategori")[:110]
            slug = base_slug
            counter = 2

            while slug in existing_slugs:
                slug = f"{base_slug[:104]}-{counter}"
                counter += 1

            existing_slugs.add(slug)
            categories_to_create.append(Category(name=category_name, slug=slug))

        Category.objects.bulk_create(
            categories_to_create,
            batch_size=BATCH_SIZE,
            ignore_conflicts=True,
        )

        existing_categories = {
            category.name: category
            for category in Category.objects.filter(name__in=normalized_names)
        }

    return existing_categories


def validate_raw_csv_columns(columns):
    date_column = find_column(
        columns,
        ["date", "tanggal", "day", "Date", "Tanggal"],
    )
    path_column = find_column(
        columns,
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
        columns,
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
        raise ValueError(
            "Kolom CSV tidak lengkap. Kolom wajib: date, page_path, views. "
            f"Kolom yang belum ditemukan: {', '.join(missing_columns)}."
        )

    return date_column, path_column, views_column


def validate_daily_category_columns(columns):
    date_column = find_column(columns, ["date", "tanggal", "Date", "Tanggal"])
    category_column = find_column(columns, ["category", "kategori", "Category", "Kategori"])
    views_column = find_column(columns, ["views", "page_views", "Views", "Page views"])

    missing_columns = []

    if not date_column:
        missing_columns.append("date")

    if not category_column:
        missing_columns.append("category")

    if not views_column:
        missing_columns.append("views")

    if missing_columns:
        raise ValueError(
            "Kolom CSV tidak lengkap. Kolom wajib: date, category, views. "
            f"Kolom yang belum ditemukan: {', '.join(missing_columns)}."
        )

    return date_column, category_column, views_column


def build_raw_traffic_map(file_obj):
    try:
        headers = pd.read_csv(file_obj, nrows=0).columns
    except pd.errors.EmptyDataError:
        return {}, ImportResult()

    date_column, path_column, views_column = validate_raw_csv_columns(headers)
    file_obj.seek(0)

    traffic_map = {}
    result = ImportResult()

    for chunk in pd.read_csv(file_obj, chunksize=CSV_CHUNK_SIZE):
        if chunk.empty:
            continue

        result.processed_rows += len(chunk)

        for row_data in chunk.to_dict("records"):
            traffic_date = parse_date_value(row_data.get(date_column))
            page_path = clean_page_path(row_data.get(path_column))
            views = parse_views_value(row_data.get(views_column, 0))

            if not traffic_date or views is None:
                result.skipped_count += 1
                continue

            category_name = detect_category_from_path(page_path)

            if category_name in EXCLUDED_FORECAST_CATEGORIES:
                result.skipped_count += 1
                continue

            key = (category_name, traffic_date, page_path)

            if key not in traffic_map:
                traffic_map[key] = {
                    "category_name": category_name,
                    "date": traffic_date,
                    "page_path": page_path,
                    "views": 0,
                }

            traffic_map[key]["views"] += views
            result.valid_rows += 1

    result.duplicate_in_file_count = result.valid_rows - len(traffic_map)

    return traffic_map, result


def build_daily_category_traffic_map(file_obj):
    try:
        headers = pd.read_csv(file_obj, nrows=0).columns
    except pd.errors.EmptyDataError:
        return {}, ImportResult()

    date_column, category_column, views_column = validate_daily_category_columns(headers)
    file_obj.seek(0)

    traffic_map = {}
    result = ImportResult()

    for chunk in pd.read_csv(file_obj, chunksize=CSV_CHUNK_SIZE):
        if chunk.empty:
            continue

        result.processed_rows += len(chunk)

        for row_data in chunk.to_dict("records"):
            traffic_date = parse_date_value(row_data.get(date_column))
            category_name = str(row_data.get(category_column, "")).strip()
            views = parse_views_value(row_data.get(views_column, 0))

            if not traffic_date or not category_name or views is None:
                result.skipped_count += 1
                continue

            key = (category_name, traffic_date, None)

            if key not in traffic_map:
                traffic_map[key] = {
                    "category_name": category_name,
                    "date": traffic_date,
                    "page_path": None,
                    "views": 0,
                }

            traffic_map[key]["views"] += views
            result.valid_rows += 1

    result.duplicate_in_file_count = result.valid_rows - len(traffic_map)

    return traffic_map, result


def get_existing_keys(items):
    if not items:
        return set()

    query = Q()

    for item in items:
        page_path = item["page_path"]
        item_query = Q(
            category_id=item["category_id"],
            date=item["date"],
        )

        if page_path is None:
            item_query &= Q(page_path__isnull=True)
        else:
            item_query &= Q(page_path=page_path)

        query |= item_query

    return set(
        TrafficData.objects
        .filter(query)
        .values_list("category_id", "date", "page_path")
    )


def flush_traffic_buffer(buffer):
    if not buffer:
        return 0

    TrafficData.objects.bulk_create(
        buffer,
        batch_size=BATCH_SIZE,
    )
    created_count = len(buffer)
    buffer.clear()

    return created_count


def import_traffic_map(traffic_map, result):
    if not traffic_map:
        return result

    with transaction.atomic():
        category_cache = build_category_cache(
            item["category_name"]
            for item in traffic_map.values()
        )

        batch = []
        buffer = []
        created_dates = []

        for item in traffic_map.values():
            category = category_cache[item["category_name"]]
            batch.append({
                **item,
                "category": category,
                "category_id": category.id,
            })

            if len(batch) >= BATCH_SIZE:
                created_count, batch_created_dates = import_traffic_batch(batch, buffer)
                result.created_count += created_count
                created_dates.extend(batch_created_dates)
                batch.clear()

        if batch:
            created_count, batch_created_dates = import_traffic_batch(batch, buffer)
            result.created_count += created_count
            created_dates.extend(batch_created_dates)

        result.total_categories = Category.objects.count()

    if result.created_count:
        result.first_date = min(created_dates)
        result.last_date = max(created_dates)

    return result


def import_traffic_batch(batch, buffer):
    existing_keys = get_existing_keys(batch)
    created_dates = []

    for item in batch:
        existing_key = (
            item["category_id"],
            item["date"],
            item["page_path"],
        )

        if existing_key in existing_keys:
            continue

        buffer.append(
            TrafficData(
                category=item["category"],
                date=item["date"],
                page_path=item["page_path"],
                views=item["views"],
            )
        )
        created_dates.append(item["date"])

    created_count = flush_traffic_buffer(buffer)

    return created_count, created_dates


def import_raw_traffic_csv(file_obj):
    traffic_map, result = build_raw_traffic_map(file_obj)
    result = import_traffic_map(traffic_map, result)
    result.duplicate_in_database_count = (
        len(traffic_map) - result.created_count
    )

    return result


def import_daily_category_csv(file_obj):
    traffic_map, result = build_daily_category_traffic_map(file_obj)
    result = import_traffic_map(traffic_map, result)
    result.duplicate_in_database_count = (
        len(traffic_map) - result.created_count
    )

    return result
