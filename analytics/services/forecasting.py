import math
import warnings
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd
from django.db.models import Max
from statsmodels.tsa.arima.model import ARIMA

from analytics.models import Category, ForecastRun, Prediction, TrafficData


warnings.filterwarnings("ignore")

MIN_ARIMA_SERIES_LENGTH = 60
MIN_ARIMA_TRAIN_LENGTH = 30
MIN_ACTIVE_DAYS = 14
TRAIN_RATIO = 0.8
FALLBACK_WINDOW = 7
MAX_MODEL_CONFIDENCE_WIDTH = 200
MAX_PREDICTION_MULTIPLIER = 12
WMAPE_TIE_TOLERANCE = 5
MAX_TUNING_SERIES_LENGTH = 180
MAX_TEST_LENGTH = 28
MAX_MODEL_ITERATIONS = 35
ARIMA_ORDERS = [
    (1, 1, 1),
    (1, 0, 1),
    (2, 1, 1),
    (2, 0, 1),
    (0, 1, 1),
]


@dataclass
class ModelCandidate:
    fitted_model: object
    order: tuple
    seasonal_order: tuple
    model_name: str
    mae: float
    rmse: float
    mape: float
    wmape: float
    smape: float
    aic: float
    bic: float


def safe_positive_int(value):
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError, OverflowError):
        value = 0

    return max(0, value)


def safe_float(value):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if math.isnan(value) or math.isinf(value):
        return None

    return round(value, 4)


def normalize_forecast_days(value, default=7, minimum=1, maximum=30):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default

    return max(minimum, min(value, maximum))


def get_model_field_names(model_class):
    return {field.name for field in model_class._meta.fields}


def get_latest_traffic_date():
    return TrafficData.objects.aggregate(latest_date=Max("date"))["latest_date"]


def prepare_time_series(category, end_date=None):
    """
    Build a daily category time series from TrafficData.

    Missing dates are filled with 0 because absent daily traffic rows should not
    be interpreted as unknown positive traffic in this dashboard workflow.
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

    if end_date:
        end_date = pd.to_datetime(end_date)

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
        .sort_index()
    )

    if end_date and not series.empty and series.index.max() < end_date:
        full_index = pd.date_range(series.index.min(), end_date, freq="D")
        series = series.reindex(full_index, fill_value=0)

    return series.astype(float)


def train_test_split_series(series):
    """
    Split only histories that are long enough for ARIMA evaluation.

    For 90+ days, use an 80/20 split. For 60-89 days, keep the latest 14 days
    as test data so the model is evaluated against recent editorial traffic.
    """
    if series is None or series.empty:
        return None, None

    if len(series) < MIN_ARIMA_SERIES_LENGTH:
        return series, pd.Series(dtype=float)

    tuning_series = series.tail(MAX_TUNING_SERIES_LENGTH)

    if len(tuning_series) >= 90:
        split_index = int(len(tuning_series) * TRAIN_RATIO)
        split_index = min(split_index, len(tuning_series) - 14)
    else:
        split_index = len(tuning_series) - 14

    split_index = max(1, split_index)

    train_series = tuning_series.iloc[:split_index]
    test_series = tuning_series.iloc[split_index:].tail(MAX_TEST_LENGTH)

    return train_series, test_series


def calculate_metrics(actual, predicted):
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)

    if len(actual_values) == 0 or len(predicted_values) == 0:
        return {
            "mae": None,
            "rmse": None,
            "mape": None,
        }

    length = min(len(actual_values), len(predicted_values))
    actual_values = actual_values[:length]
    predicted_values = predicted_values[:length]

    errors = actual_values - predicted_values
    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(np.square(errors)))
    actual_sum = np.sum(np.abs(actual_values))
    denominator = (np.abs(actual_values) + np.abs(predicted_values)) / 2

    nonzero_mask = actual_values != 0

    if nonzero_mask.any():
        mape = np.mean(
            np.abs(
                (actual_values[nonzero_mask] - predicted_values[nonzero_mask]) /
                actual_values[nonzero_mask]
            )
        ) * 100
    else:
        mape = None

    if actual_sum > 0:
        wmape = (np.sum(np.abs(errors)) / actual_sum) * 100
    else:
        wmape = None

    smape_mask = denominator > 0

    if smape_mask.any():
        smape = np.mean(np.abs(errors[smape_mask]) / denominator[smape_mask]) * 100
    else:
        smape = None

    return {
        "mae": safe_float(mae),
        "rmse": safe_float(rmse),
        "mape": safe_float(mape),
        "wmape": safe_float(wmape),
        "smape": safe_float(smape),
    }


def get_recent_baseline(series):
    if series is None or series.empty:
        return 0

    window = 14 if len(series) >= 14 else FALLBACK_WINDOW
    recent_series = series.tail(window)

    if recent_series.empty:
        return 0

    return safe_positive_int(recent_series.mean())


def get_moving_average_window(series):
    if series is None:
        return FALLBACK_WINDOW

    return 14 if len(series) >= 14 else FALLBACK_WINDOW


def evaluate_moving_average(train_series, test_series):
    if train_series is None or train_series.empty or test_series is None or test_series.empty:
        return None

    window = get_moving_average_window(train_series)
    baseline = safe_positive_int(train_series.tail(window).mean())
    predicted_values = [baseline] * len(test_series)

    return calculate_metrics(test_series, predicted_values)


def run_moving_average_fallback(series, forecast_days=7, reason="fallback"):
    if series is None or series.empty:
        return []

    last_date = series.index.max().date()
    predicted_value = get_recent_baseline(series)
    window = min(get_moving_average_window(series), len(series))
    metrics = calculate_metrics(
        series.tail(window),
        [predicted_value] * window,
    )
    mae_width = safe_positive_int(metrics["mae"] or 0)
    lower_bound = max(0, predicted_value - mae_width)
    upper_bound = max(predicted_value, predicted_value + mae_width)

    results = []

    for day in range(1, forecast_days + 1):
        prediction_date = last_date + timedelta(days=day)
        results.append({
            "prediction_date": prediction_date,
            "predicted_views": predicted_value,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "model_name": "Moving Average Fallback",
            "arima_order": "",
            "seasonal_order": "",
            "mae": metrics["mae"],
            "rmse": metrics["rmse"],
            "mape": metrics["mape"],
            "wmape": metrics["wmape"],
            "smape": metrics["smape"],
            "aic": None,
            "bic": None,
            "fallback_reason": reason,
        })

    return results


def is_sparse_or_inactive_series(series):
    if series is None or series.empty:
        return True

    nonzero_series = series[series > 0]

    if len(nonzero_series) < MIN_ACTIVE_DAYS:
        return True

    return False


def inverse_transform_forecast(values):
    return np.maximum(0, np.expm1(values))


def is_extreme_prediction(predicted_values, series):
    if len(predicted_values) == 0:
        return True

    historical_max = max(float(series.max()), 1.0)
    predicted_max = float(np.max(predicted_values))

    return predicted_max > historical_max * MAX_PREDICTION_MULTIPLIER


def fit_candidate(train_series, test_series, order):
    transformed_train = np.log1p(train_series.astype(float))

    fitted_model = ARIMA(
        transformed_train,
        order=order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(method_kwargs={"maxiter": MAX_MODEL_ITERATIONS})

    if not getattr(fitted_model, "mle_retvals", {}).get("converged", True):
        return None

    forecast_result = fitted_model.get_forecast(steps=len(test_series))
    predicted_values = inverse_transform_forecast(forecast_result.predicted_mean)

    if is_extreme_prediction(predicted_values, train_series):
        return None

    metrics = calculate_metrics(test_series, predicted_values)

    if metrics["wmape"] is None:
        sort_wmape = float("inf")
    else:
        sort_wmape = metrics["wmape"]

    if math.isinf(sort_wmape):
        return None

    return ModelCandidate(
        fitted_model=fitted_model,
        order=order,
        seasonal_order=(0, 0, 0, 0),
        model_name="ARIMA",
        mae=metrics["mae"],
        rmse=metrics["rmse"],
        mape=metrics["mape"],
        wmape=metrics["wmape"],
        smape=metrics["smape"],
        aic=safe_float(fitted_model.aic),
        bic=safe_float(fitted_model.bic),
    )


def is_better_candidate(candidate, best_candidate):
    if best_candidate is None:
        return True

    candidate_wmape = candidate.wmape if candidate.wmape is not None else float("inf")
    best_wmape = best_candidate.wmape if best_candidate.wmape is not None else float("inf")

    if candidate_wmape < best_wmape - WMAPE_TIE_TOLERANCE:
        return True

    if abs(candidate_wmape - best_wmape) <= WMAPE_TIE_TOLERANCE:
        candidate_aic = candidate.aic if candidate.aic is not None else float("inf")
        best_aic = best_candidate.aic if best_candidate.aic is not None else float("inf")

        if candidate_aic < best_aic:
            return True

        if candidate_aic == best_aic:
            candidate_bic = candidate.bic if candidate.bic is not None else float("inf")
            best_bic = best_candidate.bic if best_candidate.bic is not None else float("inf")
            return candidate_bic < best_bic

    return False


def find_best_arima_model(series):
    train_series, test_series = train_test_split_series(series)

    if (
        train_series is None or
        test_series is None or
        len(train_series) < MIN_ARIMA_TRAIN_LENGTH or
        len(test_series) == 0 or
        train_series.nunique() <= 1
    ):
        return None

    best_candidate = None

    for order in ARIMA_ORDERS:
        try:
            candidate = fit_candidate(
                train_series=train_series,
                test_series=test_series,
                order=order,
            )
        except Exception:
            continue

        if candidate and is_better_candidate(candidate, best_candidate):
            best_candidate = candidate

    return best_candidate


def get_average_confidence_width(results):
    confidence_widths = []

    for item in results:
        predicted_value = item["predicted_views"]

        if predicted_value <= 0:
            continue

        confidence_widths.append(
            ((item["upper_bound"] - item["lower_bound"]) / predicted_value) * 100
        )

    if not confidence_widths:
        return 0

    return sum(confidence_widths) / len(confidence_widths)


def format_order(order):
    if not order:
        return ""

    return f"({','.join(str(value) for value in order)})"


def build_forecast_results(series, candidate, forecast_days):
    transformed_series = np.log1p(series.astype(float))

    refit_model = ARIMA(
        transformed_series,
        order=candidate.order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(method_kwargs={"maxiter": MAX_MODEL_ITERATIONS})

    forecast_result = refit_model.get_forecast(steps=forecast_days)
    predicted_mean = inverse_transform_forecast(forecast_result.predicted_mean)
    confidence_interval = np.expm1(forecast_result.conf_int(alpha=0.05))
    confidence_interval = np.maximum(0, confidence_interval)

    results = []
    order_label = format_order(candidate.order)
    model_name = f"ARIMA{order_label}"

    for prediction_date, predicted_value in predicted_mean.items():
        lower_value = confidence_interval.loc[prediction_date].iloc[0]
        upper_value = confidence_interval.loc[prediction_date].iloc[1]
        predicted_views = safe_positive_int(predicted_value)
        lower_bound = safe_positive_int(lower_value)
        upper_bound = max(predicted_views, safe_positive_int(upper_value))

        results.append({
            "prediction_date": prediction_date.date(),
            "predicted_views": predicted_views,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "model_name": model_name,
            "arima_order": order_label,
            "seasonal_order": "",
            "mae": candidate.mae,
            "rmse": candidate.rmse,
            "mape": candidate.mape,
            "wmape": candidate.wmape,
            "smape": candidate.smape,
            "aic": safe_float(refit_model.aic),
            "bic": safe_float(refit_model.bic),
        })

    return results


def forecast_with_best_model(series, forecast_days=7):
    if series is None or series.empty:
        return []

    if len(series) < MIN_ARIMA_SERIES_LENGTH:
        return run_moving_average_fallback(
            series=series,
            forecast_days=forecast_days,
            reason="history_too_short",
        )

    active_days = int((series > 0).sum())

    if active_days < MIN_ACTIVE_DAYS:
        return run_moving_average_fallback(
            series=series,
            forecast_days=forecast_days,
            reason="active_days_too_low",
        )

    try:
        train_series, test_series = train_test_split_series(series)
        candidate = find_best_arima_model(series)

        if not candidate:
            return run_moving_average_fallback(
                series=series,
                forecast_days=forecast_days,
                reason="no_valid_arima_candidate",
            )

        results = build_forecast_results(
            series=series,
            candidate=candidate,
            forecast_days=forecast_days,
        )

        fallback_metrics = evaluate_moving_average(train_series, test_series)

        if (
            fallback_metrics and
            fallback_metrics["wmape"] is not None and
            candidate.wmape is not None and
            fallback_metrics["wmape"] + WMAPE_TIE_TOLERANCE < candidate.wmape
        ):
            return run_moving_average_fallback(
                series=series,
                forecast_days=forecast_days,
                reason="moving_average_more_stable",
            )

        has_zero_prediction_interval = any(
            item["predicted_views"] <= 0 and item["upper_bound"] > 0
            for item in results
        )

        if (
            has_zero_prediction_interval or
            get_average_confidence_width(results) > MAX_MODEL_CONFIDENCE_WIDTH
        ):
            return run_moving_average_fallback(
                series=series,
                forecast_days=forecast_days,
                reason="model_interval_too_wide",
            )

        return results

    except Exception as error:
        print(f"Forecast error: {error}")

        return run_moving_average_fallback(
            series=series,
            forecast_days=forecast_days,
            reason="model_error",
        )


def run_arima(series, forecast_days=7):
    return forecast_with_best_model(series=series, forecast_days=forecast_days)


def build_prediction_kwargs(category, item, forecast_run=None):
    prediction_fields = get_model_field_names(Prediction)

    prediction_kwargs = {
        "category": category,
        "prediction_date": item["prediction_date"],
        "predicted_views": item["predicted_views"],
        "lower_bound": item["lower_bound"],
        "upper_bound": item["upper_bound"],
        "model_name": item["model_name"],
    }

    optional_field_map = {
        "arima_order": "arima_order",
        "seasonal_order": "seasonal_order",
        "mae": "mae",
        "rmse": "rmse",
        "mape": "mape",
        "wmape": "wmape",
        "smape": "smape",
        "aic": "aic",
        "bic": "bic",
    }

    for model_field, item_key in optional_field_map.items():
        if model_field in prediction_fields:
            prediction_kwargs[model_field] = item.get(item_key)

    if forecast_run and "forecast_run" in prediction_fields:
        prediction_kwargs["forecast_run"] = forecast_run

    return prediction_kwargs


def generate_forecast_for_category(category, forecast_days=7, forecast_run=None):
    series = prepare_time_series(
        category=category,
        end_date=get_latest_traffic_date(),
    )

    forecast_results = forecast_with_best_model(
        series=series,
        forecast_days=forecast_days,
    )

    if not forecast_results:
        return 0

    prediction_objects = [
        Prediction(**build_prediction_kwargs(category, item, forecast_run))
        for item in forecast_results
    ]

    Prediction.objects.bulk_create(prediction_objects, batch_size=500)

    return len(prediction_objects)


def generate_all_forecasts(forecast_days=7, forecast_run=None):
    forecast_days = normalize_forecast_days(forecast_days)
    total_created = 0
    failed_categories = []

    categories = Category.objects.all().order_by("name")

    for category in categories:
        try:
            created_count = generate_forecast_for_category(
                category=category,
                forecast_days=forecast_days,
                forecast_run=forecast_run,
            )
            total_created += created_count
        except Exception as error:
            failed_categories.append(f"{category.name}: {error}")

    return {
        "total_categories": categories.count(),
        "total_predictions": total_created,
        "failed_categories": failed_categories,
    }


def create_forecast_run_and_generate(forecast_days=7):
    forecast_days = normalize_forecast_days(forecast_days)
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
        summary = generate_all_forecasts(
            forecast_days=forecast_days,
            forecast_run=forecast_run,
        )
        total_created = summary["total_predictions"]
        failed_categories = summary["failed_categories"]

        if failed_categories:
            error_message = " | ".join(failed_categories)
            if "error_message" in forecast_run_fields:
                forecast_run.error_message = error_message[:2000]

        if hasattr(forecast_run, "mark_success"):
            forecast_run.mark_success(total_predictions=total_created)

            if failed_categories and "error_message" in forecast_run_fields:
                forecast_run.error_message = " | ".join(failed_categories)[:2000]
                forecast_run.save(update_fields=["error_message"])
        else:
            update_fields = []

            if "status" in forecast_run_fields:
                forecast_run.status = success_status
                update_fields.append("status")

            if "total_predictions" in forecast_run_fields:
                forecast_run.total_predictions = total_created
                update_fields.append("total_predictions")

            if "error_message" in forecast_run_fields and failed_categories:
                forecast_run.error_message = " | ".join(failed_categories)[:2000]
                update_fields.append("error_message")

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
