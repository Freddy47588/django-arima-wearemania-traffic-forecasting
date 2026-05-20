import warnings

import pandas as pd
from django.db import transaction
from django.utils import timezone
from statsmodels.tsa.arima.model import ARIMA

from analytics.models import Category, TrafficData, Prediction, ForecastRun


warnings.filterwarnings("ignore")


MINIMUM_DATA_POINTS = 10


def prepare_time_series(category):
    """
    Mengambil data traffic berdasarkan kategori,
    lalu mengubahnya menjadi time series harian.
    """

    queryset = (
        TrafficData.objects
        .filter(category=category)
        .values("date", "views")
        .order_by("date")
    )

    df = pd.DataFrame(list(queryset))

    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])

    daily_df = (
        df.groupby("date")["views"]
        .sum()
        .reset_index()
        .sort_values("date")
    )

    series = (
        daily_df
        .set_index("date")["views"]
        .asfreq("D")
        .fillna(0)
    )

    return series


def moving_average_fallback(series, forecast_days=7):
    """
    Fallback sederhana kalau data terlalu sedikit
    atau ARIMA gagal fitting.

    Ini bukan model utama, hanya penyelamat agar sistem tetap menghasilkan output.
    """

    if series is None or len(series) == 0:
        return []

    last_date = series.index.max()
    window = min(7, len(series))
    average_value = series.tail(window).mean()

    results = []

    for step in range(1, forecast_days + 1):
        prediction_date = last_date + pd.Timedelta(days=step)
        predicted_views = max(0, round(float(average_value)))

        results.append({
            "prediction_date": prediction_date.date(),
            "predicted_views": predicted_views,
            "lower_bound": max(0, round(predicted_views * 0.8)),
            "upper_bound": round(predicted_views * 1.2),
            "model_order": "MovingAverageFallback",
        })

    return results


def run_arima_forecast(series, forecast_days=7):
    """
    Menjalankan ARIMA untuk satu time series.

    Model awal memakai beberapa kandidat order sederhana.
    Sistem memilih model dengan AIC terbaik.
    """

    if series is None or len(series) < MINIMUM_DATA_POINTS:
        return moving_average_fallback(series, forecast_days)

    candidate_orders = [
        (1, 1, 1),
        (2, 1, 1),
        (1, 1, 2),
        (2, 1, 2),
    ]

    best_model_fit = None
    best_order = None
    best_aic = None

    for order in candidate_orders:
        try:
            model = ARIMA(series, order=order)
            model_fit = model.fit()

            if best_aic is None or model_fit.aic < best_aic:
                best_model_fit = model_fit
                best_order = order
                best_aic = model_fit.aic

        except Exception:
            continue

    if best_model_fit is None:
        return moving_average_fallback(series, forecast_days)

    try:
        forecast_result = best_model_fit.get_forecast(steps=forecast_days)
        predicted_mean = forecast_result.predicted_mean
        confidence_interval = forecast_result.conf_int()

        results = []

        for date, value in predicted_mean.items():
            lower = confidence_interval.loc[date].iloc[0]
            upper = confidence_interval.loc[date].iloc[1]

            predicted_views = max(0, round(float(value)))
            lower_bound = max(0, round(float(lower)))
            upper_bound = max(0, round(float(upper)))

            results.append({
                "prediction_date": date.date(),
                "predicted_views": predicted_views,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "model_order": f"ARIMA{best_order}",
            })

        return results

    except Exception:
        return moving_average_fallback(series, forecast_days)


def generate_forecast_for_category(category, forecast_run, forecast_days=7):
    """
    Generate forecast untuk satu kategori,
    lalu menyimpan hasilnya ke tabel Prediction.
    """

    series = prepare_time_series(category)
    forecast_results = run_arima_forecast(series, forecast_days)

    if not forecast_results:
        return 0

    prediction_objects = []

    for item in forecast_results:
        prediction_objects.append(
            Prediction(
                forecast_run=forecast_run,
                category=category,
                prediction_date=item["prediction_date"],
                predicted_views=item["predicted_views"],
                lower_bound=item["lower_bound"],
                upper_bound=item["upper_bound"],
                model_order=item["model_order"],
            )
        )

    Prediction.objects.bulk_create(prediction_objects)

    return len(prediction_objects)


@transaction.atomic
def generate_all_forecasts(forecast_days=7):
    """
    Generate forecast untuk semua kategori.

    Fungsi ini cocok dipanggil dari:
    - tombol dashboard
    - management command
    - cron job / scheduled task
    - proses setelah sync GA4 API
    """

    forecast_run = ForecastRun.objects.create(
        model_name="ARIMA",
        forecast_days=forecast_days,
        status="running",
    )

    try:
        categories = Category.objects.all()
        total_predictions = 0

        for category in categories:
            created_count = generate_forecast_for_category(
                category=category,
                forecast_run=forecast_run,
                forecast_days=forecast_days,
            )
            total_predictions += created_count

        forecast_run.status = "success"
        forecast_run.total_predictions = total_predictions
        forecast_run.message = "Forecast generated successfully."
        forecast_run.finished_at = timezone.now()
        forecast_run.save()

        return forecast_run

    except Exception as error:
        forecast_run.status = "failed"
        forecast_run.message = str(error)
        forecast_run.finished_at = timezone.now()
        forecast_run.save()

        raise error