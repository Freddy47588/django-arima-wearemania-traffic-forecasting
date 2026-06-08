import os
from datetime import datetime

from django.conf import settings
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

from .models import Category, TrafficData

# Set Path Kredensial
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(
    settings.BASE_DIR,
    "ga4_credentials.json",
)


def sync_ga4_to_db(property_id, days_back=30):
    """
    Fungsi 'All-in-One' untuk menarik data dan langsung menyimpannya ke database.
    """
    client = BetaAnalyticsDataClient()

    # Tarik data dari X hari terakhir sampai kemarin
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="date"), Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date=f"{days_back}daysAgo", end_date="yesterday")],
    )

    response = client.run_report(request)

    count = 0
    for row in response.rows:
        date_str = row.dimension_values[0].value
        path = row.dimension_values[1].value.lower()
        views = int(row.metric_values[0].value)

        # Logika Mapping URL ke Kategori Wearemania
        if "arema-fc" in path:
            cat_name = "Arema FC"
        elif "liga-1" in path or "liga-indonesia" in path:
            cat_name = "Liga 1"
        elif "kriminal" in path or "peristiwa" in path:
            cat_name = "Kriminal"
        else:
            # Abaikan path yang tidak relevan seperti /admin/ atau /login/.
            continue

        # Ambil/Buat Objek Kategori
        category_obj, _ = Category.objects.get_or_create(
            name=cat_name,
            defaults={"slug": cat_name.replace(" ", "-").lower()},
        )

        # Ubah format tanggal YYYYMMDD ke objek Date
        date_obj = datetime.strptime(date_str, "%Y%m%d").date()

        # Simpan/Update ke Database
        TrafficData.objects.update_or_create(
            category=category_obj,
            date=date_obj,
            page_path=path,
            defaults={"views": views},
        )
        count += 1

    return f"Berhasil sinkronisasi {count} baris data."
