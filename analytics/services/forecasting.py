import warnings
from datetime import timedelta

import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from analytics.models import Category, ForecastRun, Prediction, TrafficData


warnings.filterwarnings("ignore")


def safe_positive_int(value):
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        value = 0

    return max(0, value)


def get_model_field_names(model_class):
    return {field.name for field in model_class._meta.fields}


def prepare_time_series(category):
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
        df.groupby("date", as_index=False)["views"]
        .sum()
        .sort_values("date")
    )

    series = (
        daily_df
        .set_index("date")["views"]
        .asfreq("D")
        .fillna(0)
    )

    return series


def run_moving_average_fallback(series, forecast_days=7):
    if series is None or series.empty:
        return []

    last_date = series.index.max().date()
    recent_series = series.tail(7)

    if recent_series.empty:
        average_value = 0
    else:
        average_value = recent_series.mean()

    predicted_value = safe_positive_int(average_value)

    results = []

    for day in range(1, forecast_days + 1):
        prediction_date = last_date + timedelta(days=day)

        lower_bound = safe_positive_int(predicted_value * 0.8)
        upper_bound = safe_positive_int(predicted_value * 1.2)

        results.append({
            "prediction_date": prediction_date,
            "predicted_views": predicted_value,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "model_name": "Moving Average Fallback",
        })

    return results


def run_arima(series, forecast_days=7):
    if series is None or series.empty:
        return []

    if len(series) < 10:
        return run_moving_average_fallback(
            series=series,
            forecast_days=forecast_days,
        )

    if series.nunique() <= 1:
        return run_moving_average_fallback(
            series=series,
            forecast_days=forecast_days,
        )

    try:
        model = ARIMA(series, order=(1, 1, 1))
        fitted_model = model.fit()

        forecast_result = fitted_model.get_forecast(steps=forecast_days)
        predicted_mean = forecast_result.predicted_mean
        confidence_interval = forecast_result.conf_int()

        results = []

        for prediction_date, predicted_value in predicted_mean.items():
            lower_value = confidence_interval.loc[prediction_date].iloc[0]
            upper_value = confidence_interval.loc[prediction_date].iloc[1]

            results.append({
                "prediction_date": prediction_date.date(),
                "predicted_views": safe_positive_int(predicted_value),
                "lower_bound": safe_positive_int(lower_value),
                "upper_bound": safe_positive_int(upper_value),
                "model_name": "ARIMA(1,1,1)",
            })

        return results

    except Exception as error:
        print(f"ARIMA error: {error}")

        return run_moving_average_fallback(
            series=series,
            forecast_days=forecast_days,
        )


def generate_forecast_for_category(category, forecast_days=7, forecast_run=None):
    series = prepare_time_series(category)

    forecast_results = run_arima(
        series=series,
        forecast_days=forecast_days,
    )

    if not forecast_results:
        return 0

    prediction_fields = get_model_field_names(Prediction)

    prediction_objects = []

    for item in forecast_results:
        prediction_kwargs = {
            "category": category,
            "prediction_date": item["prediction_date"],
            "predicted_views": item["predicted_views"],
            "lower_bound": item["lower_bound"],
            "upper_bound": item["upper_bound"],
            "model_name": item["model_name"],
        }

        if forecast_run and "forecast_run" in prediction_fields:
            prediction_kwargs["forecast_run"] = forecast_run

        prediction_objects.append(Prediction(**prediction_kwargs))

    Prediction.objects.bulk_create(prediction_objects, batch_size=500)

    return len(prediction_objects)


def generate_all_forecasts(forecast_days=7, forecast_run=None):
    total_created = 0

    categories = Category.objects.all().order_by("name")

    for category in categories:
        created_count = generate_forecast_for_category(
            category=category,
            forecast_days=forecast_days,
            forecast_run=forecast_run,
        )

        total_created += created_count

    return total_created


def create_forecast_run_and_generate(forecast_days=7):
    forecast_run_fields = get_model_field_names(ForecastRun)

    running_status = getattr(ForecastRun, "STATUS_RUNNING", "running")
    success_status = getattr(ForecastRun, "STATUS_SUCCESS", "success")
    failed_status = getattr(ForecastRun, "STATUS_FAILED", "failed")

    create_kwargs = {}

    if "status" in forecast_run_fields:
        create_kwargs["status"] = running_status

    if "forecast_days" in forecast_run_fields:
        create_kwargs["forecast_days"] = forecast_days

    forecast_run = ForecastRun.objects.create(**create_kwargs)

    try:
        total_created = generate_all_forecasts(
            forecast_days=forecast_days,
            forecast_run=forecast_run,
        )

        if hasattr(forecast_run, "mark_success"):
            forecast_run.mark_success(total_predictions=total_created)
        else:
            update_fields = []

            if "status" in forecast_run_fields:
                forecast_run.status = success_status
                update_fields.append("status")

            if "total_predictions" in forecast_run_fields:
                forecast_run.total_predictions = total_created
                update_fields.append("total_predictions")

            if update_fields:
                forecast_run.save(update_fields=update_fields)
            else:
                forecast_run.save()

    except Exception as error:
        if hasattr(forecast_run, "mark_failed"):
            forecast_run.mark_failed(error)
        else:
            update_fields = []

            if "status" in forecast_run_fields:
                forecast_run.status = failed_status
                update_fields.append("status")

            if "error_message" in forecast_run_fields:
                forecast_run.error_message = str(error)
                update_fields.append("error_message")

            if update_fields:
                forecast_run.save(update_fields=update_fields)
            else:
                forecast_run.save()

        raise

    return forecast_run
