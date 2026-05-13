import json

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render

from .forms import UploadCSVForm
from .models import Category, TrafficData
from .services.data_cleaning import process_raw_csv


def dashboard(request):
    selected_category = request.GET.get("category")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    traffic_queryset = TrafficData.objects.select_related("category").all()

    if selected_category:
        traffic_queryset = traffic_queryset.filter(category_id=selected_category)

    if start_date:
        traffic_queryset = traffic_queryset.filter(date__gte=start_date)

    if end_date:
        traffic_queryset = traffic_queryset.filter(date__lte=end_date)

    daily_data = (
        traffic_queryset
        .values("date")
        .annotate(total_views=Sum("views"))
        .order_by("date")
    )

    actual_labels = [item["date"].strftime("%Y-%m-%d") for item in daily_data]
    actual_views = [int(item["total_views"] or 0) for item in daily_data]

    category_data = (
        TrafficData.objects
        .values("category__name")
        .annotate(total_views=Sum("views"))
        .order_by("-total_views")[:10]
    )

    category_labels = [item["category__name"] for item in category_data]
    category_views = [int(item["total_views"] or 0) for item in category_data]

    total_views = traffic_queryset.aggregate(total=Sum("views"))["total"] or 0

    context = {
        "categories": Category.objects.all().order_by("name"),
        "selected_category": selected_category,
        "start_date": start_date or "",
        "end_date": end_date or "",

        "total_views": f"{total_views:,}".replace(",", "."),
        "total_categories": Category.objects.count(),
        "total_records": f"{TrafficData.objects.count():,}".replace(",", "."),
        "forecast_horizon": 7,

        "actual_labels": json.dumps(actual_labels),
        "actual_views": json.dumps(actual_views),

        "forecast_labels": json.dumps([]),
        "forecast_views": json.dumps([]),
        "forecast_lower": json.dumps([]),
        "forecast_upper": json.dumps([]),

        "category_labels": json.dumps(category_labels),
        "category_views": json.dumps(category_views),

        "top_forecast_categories": [],
        "recommendation_text": "",
        "predictions": [],
        "import_logs": [],
    }

    return render(request, "analytics/dashboard.html", context)


def upload_raw_data(request):
    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)

        if form.is_valid():
            csv_file = request.FILES["csv_file"]

            try:
                daily_category, info = process_raw_csv(csv_file)

                imported_rows = 0

                for _, row in daily_category.iterrows():
                    category, _ = Category.objects.get_or_create(
                        name=row["category"]
                    )

                    TrafficData.objects.update_or_create(
                        category=category,
                        date=row["date"],
                        defaults={"views": int(row["views"])}
                    )

                    imported_rows += 1

                messages.success(
                    request,
                    (
                        f"Import berhasil. "
                        f"{imported_rows} data harian kategori disimpan. "
                        f"Periode {info['date_start']} sampai {info['date_end']}. "
                        f"Total kategori: {info['category_count']}."
                    )
                )

                return redirect("dashboard")

            except Exception as e:
                messages.error(request, f"Import gagal: {e}")

    else:
        form = UploadCSVForm()

    return render(request, "analytics/upload_raw_data.html", {"form": form})