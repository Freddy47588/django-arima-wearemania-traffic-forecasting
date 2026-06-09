import math
import warnings
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd
from django.conf import settings
from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX

from analytics.models import Category, ForecastRun, Prediction, TrafficData


warnings.filterwarnings("ignore")

DEFAULT_FORECAST_DAYS = 7
MAX_FORECAST_DAYS = 14
MIN_ARIMA_SERIES_LENGTH = 60
MIN_ACTIVE_DAYS = 14
FALLBACK_WINDOW = 7
MAX_MODEL_ITERATIONS = 35
MAX_PREDICTION_MULTIPLIER = 12
BASELINE_ARIMA_TOLERANCE = 1.15

ARIMA_CANDIDATES = [
    (1, 1, 1),
    (1, 0, 1),
    (2, 1, 1),
    (2, 0, 1),
    (0, 1, 1),
    (1, 1, 0),
    (0, 1, 2),
]

SARIMA_CANDIDATES = [
    ((1, 1, 1), (1, 0, 1, 7)),
    ((1, 0, 1), (1, 0, 1, 7)),
]


@dataclass
class SeriesProfile:
    total_days: int
    active_days: int
    zero_ratio: float
    total_views: float
    is_constant: bool


@dataclass
class EvaluatedModel:
    order: tuple
    seasonal_order: tuple
    model_name: str
    mae: float | None
    rmse: float | None
    mape: float | None
    wmape: float | None
    smape: float | None
    aic: float | None
    bic: float | None


@dataclass
class ForecastSummary:
    total_categories: int
    total_predictions: int
    successful_categories: int
    fallback_categories: int
    failed_categories: list
    average_wmape: float | None
    forecast_days: int


def safe_positive_int(value):
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError, OverflowError):
        value = 0

    return max(0, value)


def safe_float(value, digits=4):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if math.isnan(value) or math.isinf(value):
        return None

    return round(value, digits)


def normalize_forecast_days(value, default=None, minimum=1, maximum=None):
    default = default or getattr(settings, "DEFAULT_FORECAST_DAYS", DEFAULT_FORECAST_DAYS)
    maximum = maximum or getattr(settings, "MAX_FORECAST_DAYS", MAX_FORECAST_DAYS)

    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default

    return max(minimum, min(value, maximum))


def normalize_history_limit(value, default=10, minimum=1, maximum=100):
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
    queryset = (
        TrafficData.objects
        .filter(category=category)
        .values("date")
        .annotate(views=Sum("views"))
        .order_by("date")
    )
    df = pd.DataFrame(list(queryset))

    if df.empty:
        return pd.Series(dtype=float)

    df["date"] = pd.to_datetime(df["date"])
    df["views"] = pd.to_numeric(df["views"], errors="coerce")
    df["views"] = df["views"].replace([np.inf, -np.inf], np.nan).fillna(0)
    df["views"] = df["views"].clip(lower=0)

    series = (
        df.groupby("date")["views"]
        .sum()
        .sort_index()
        .asfreq("D")
        .fillna(0)
    )

    if end_date and not series.empty:
        end_date = pd.to_datetime(end_date)
        full_index = pd.date_range(series.index.min(), end_date, freq="D")
        series = series.reindex(full_index, fill_value=0)

    return series.astype(float).replace([np.inf, -np.inf], 0).fillna(0).clip(lower=0)


def profile_series(series):
    if series is None or series.empty:
        return SeriesProfile(0, 0, 1.0, 0, True)

    total_days = len(series)
    active_days = int((series > 0).sum())
    zero_ratio = safe_float((series == 0).sum() / total_days) or 0
    total_views = float(series.sum())

    return SeriesProfile(
        total_days=total_days,
        active_days=active_days,
        zero_ratio=zero_ratio,
        total_views=total_views,
        is_constant=series.nunique() <= 1,
    )


def is_arima_eligible(profile):
    return (
        profile.total_days >= MIN_ARIMA_SERIES_LENGTH and
        profile.active_days >= MIN_ACTIVE_DAYS and
        profile.total_views > 0 and
        not profile.is_constant
    )


def train_test_split_series(series, forecast_days):
    if series is None or series.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    forecast_days = normalize_forecast_days(forecast_days)
    test_size = min(forecast_days, MAX_FORECAST_DAYS, max(3, len(series) // 10))

    if len(series) <= test_size:
        return series, pd.Series(dtype=float)

    return series.iloc[:-test_size], series.iloc[-test_size:]


def calculate_metrics(actual, predicted):
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)

    if len(actual_values) == 0 or len(predicted_values) == 0:
        return {"mae": None, "rmse": None, "mape": None, "wmape": None, "smape": None}

    length = min(len(actual_values), len(predicted_values))
    actual_values = actual_values[:length]
    predicted_values = np.maximum(0, predicted_values[:length])
    errors = actual_values - predicted_values

    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(np.square(errors)))
    actual_sum = np.sum(np.abs(actual_values))
    nonzero_mask = actual_values > 0
    smape_denominator = (np.abs(actual_values) + np.abs(predicted_values)) / 2
    smape_mask = smape_denominator > 0

    mape = None
    if nonzero_mask.any():
        mape = (
            np.mean(np.abs(errors[nonzero_mask] / actual_values[nonzero_mask])) *
            100
        )

    wmape = None
    if actual_sum > 0:
        wmape = (np.sum(np.abs(errors)) / actual_sum) * 100

    smape = None
    if smape_mask.any():
        smape = np.mean(np.abs(errors[smape_mask]) / smape_denominator[smape_mask]) * 100

    return {
        "mae": safe_float(mae),
        "rmse": safe_float(rmse),
        "mape": safe_float(mape),
        "wmape": safe_float(wmape),
        "smape": safe_float(smape),
    }


def is_better_candidate(candidate, best_candidate):
    if best_candidate is None:
        return True

    candidate_wmape = candidate.wmape if candidate.wmape is not None else float("inf")
    best_wmape = best_candidate.wmape if best_candidate.wmape is not None else float("inf")

    if candidate_wmape != best_wmape:
        return candidate_wmape < best_wmape

    candidate_mae = candidate.mae if candidate.mae is not None else float("inf")
    best_mae = best_candidate.mae if best_candidate.mae is not None else float("inf")

    if candidate_mae != best_mae:
        return candidate_mae < best_mae

    candidate_aic = candidate.aic if candidate.aic is not None else float("inf")
    best_aic = best_candidate.aic if best_candidate.aic is not None else float("inf")

    return candidate_aic < best_aic


def is_extreme_prediction(predicted_values, series):
    if len(predicted_values) == 0:
        return True

    if np.any(np.isnan(predicted_values)) or np.any(np.isinf(predicted_values)):
        return True

    historical_max = max(float(series.max()), 1.0)
    predicted_max = float(np.max(predicted_values))

    return predicted_max > historical_max * MAX_PREDICTION_MULTIPLIER


def fit_arima_candidate(train_series, test_series, order):
    fitted_model = ARIMA(
        train_series,
        order=order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(method_kwargs={"maxiter": MAX_MODEL_ITERATIONS})

    predicted_values = np.asarray(fitted_model.forecast(steps=len(test_series)), dtype=float)
    predicted_values = np.maximum(0, predicted_values)

    if is_extreme_prediction(predicted_values, train_series):
        return None

    metrics = calculate_metrics(test_series, predicted_values)

    return EvaluatedModel(
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


def fit_sarima_candidate(train_series, test_series, order, seasonal_order):
    fitted_model = SARIMAX(
        train_series,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False, maxiter=MAX_MODEL_ITERATIONS)

    predicted_values = np.asarray(fitted_model.forecast(steps=len(test_series)), dtype=float)
    predicted_values = np.maximum(0, predicted_values)

    if is_extreme_prediction(predicted_values, train_series):
        return None

    metrics = calculate_metrics(test_series, predicted_values)

    return EvaluatedModel(
        order=order,
        seasonal_order=seasonal_order,
        model_name="SARIMA",
        mae=metrics["mae"],
        rmse=metrics["rmse"],
        mape=metrics["mape"],
        wmape=metrics["wmape"],
        smape=metrics["smape"],
        aic=safe_float(fitted_model.aic),
        bic=safe_float(fitted_model.bic),
    )


def find_best_arima_model(series, forecast_days, fast=False):
    train_series, test_series = train_test_split_series(series, forecast_days)

    if train_series.empty or test_series.empty or train_series.nunique() <= 1:
        return None

    best_candidate = None

    for order in ARIMA_CANDIDATES:
        try:
            candidate = fit_arima_candidate(train_series, test_series, order)
        except Exception:
            continue

        if candidate and is_better_candidate(candidate, best_candidate):
            best_candidate = candidate

    profile = profile_series(series)

    if not fast and profile.total_days >= 180 and profile.active_days >= 60:
        for order, seasonal_order in SARIMA_CANDIDATES:
            try:
                candidate = fit_sarima_candidate(
                    train_series,
                    test_series,
                    order,
                    seasonal_order,
                )
            except Exception:
                continue

            if candidate and is_better_candidate(candidate, best_candidate):
                best_candidate = candidate

    return best_candidate


def get_fallback_value(series):
    if series is None or series.empty:
        return 0

    recent = series.tail(FALLBACK_WINDOW)
    positive_recent = recent[recent > 0]

    if not positive_recent.empty:
        return safe_positive_int(positive_recent.median())

    return safe_positive_int(recent.mean())


def evaluate_moving_average_baseline(series, forecast_days):
    train_series, test_series = train_test_split_series(series, forecast_days)

    if train_series.empty or test_series.empty:
        recent_value = get_fallback_value(series)
        metrics = calculate_metrics(series.tail(FALLBACK_WINDOW), [recent_value] * len(series.tail(FALLBACK_WINDOW)))
        return EvaluatedModel(
            order=(),
            seasonal_order=(),
            model_name="Moving Average Fallback",
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            mape=metrics["mape"],
            wmape=metrics["wmape"],
            smape=metrics["smape"],
            aic=None,
            bic=None,
        )

    value = get_fallback_value(train_series)
    metrics = calculate_metrics(test_series, [value] * len(test_series))

    return EvaluatedModel(
        order=(),
        seasonal_order=(),
        model_name="Moving Average Fallback",
        mae=metrics["mae"],
        rmse=metrics["rmse"],
        mape=metrics["mape"],
        wmape=metrics["wmape"],
        smape=metrics["smape"],
        aic=None,
        bic=None,
    )


def should_use_fallback(arima_candidate, fallback_candidate):
    if arima_candidate is None:
        return True

    if fallback_candidate is None:
        return False

    if arima_candidate.wmape is not None and fallback_candidate.wmape is not None:
        return arima_candidate.wmape > fallback_candidate.wmape * BASELINE_ARIMA_TOLERANCE

    if arima_candidate.mae is not None and fallback_candidate.mae is not None:
        return arima_candidate.mae > fallback_candidate.mae * BASELINE_ARIMA_TOLERANCE

    return False


def format_order(order):
    if not order:
        return ""

    return f"({','.join(str(value) for value in order)})"


def build_fallback_results(series, forecast_days, candidate, reason="fallback"):
    if series is None or series.empty:
        return []

    forecast_days = normalize_forecast_days(forecast_days)
    last_date = series.index.max().date()
    prediction_value = get_fallback_value(series)
    recent = series.tail(min(FALLBACK_WINDOW, len(series)))
    std_recent = safe_positive_int(recent.std()) if len(recent) > 1 else 0
    interval_width = max(std_recent, safe_positive_int(prediction_value * 0.10))

    results = []

    for day in range(1, forecast_days + 1):
        prediction_date = last_date + timedelta(days=day)

        results.append({
            "prediction_date": prediction_date,
            "predicted_views": prediction_value,
            "lower_bound": max(0, prediction_value - interval_width),
            "upper_bound": prediction_value + interval_width,
            "model_name": "Moving Average Fallback",
            "arima_order": "",
            "seasonal_order": "",
            "mae": candidate.mae if candidate else None,
            "rmse": candidate.rmse if candidate else None,
            "mape": candidate.mape if candidate else None,
            "wmape": candidate.wmape if candidate else None,
            "smape": candidate.smape if candidate else None,
            "aic": None,
            "bic": None,
            "fallback_reason": reason,
        })

    return results


def build_model_results(series, candidate, forecast_days):
    forecast_days = normalize_forecast_days(forecast_days)
    last_date = series.index.max().date()

    if candidate.model_name == "SARIMA":
        model = SARIMAX(
            series,
            order=candidate.order,
            seasonal_order=candidate.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False, maxiter=MAX_MODEL_ITERATIONS)
    else:
        model = ARIMA(
            series,
            order=candidate.order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(method_kwargs={"maxiter": MAX_MODEL_ITERATIONS})

    forecast = model.get_forecast(steps=forecast_days)
    predicted_values = np.maximum(0, np.asarray(forecast.predicted_mean, dtype=float))

    try:
        confidence_interval = np.maximum(0, np.asarray(forecast.conf_int(alpha=0.05), dtype=float))
        lower_values = confidence_interval[:, 0]
        upper_values = confidence_interval[:, 1]
    except Exception:
        train_residuals = np.asarray(getattr(model, "resid", []), dtype=float)
        residual_std = safe_positive_int(np.nanstd(train_residuals)) if len(train_residuals) else 0
        lower_values = np.maximum(0, predicted_values - residual_std)
        upper_values = predicted_values + residual_std

    order_label = format_order(candidate.order)
    seasonal_label = format_order(candidate.seasonal_order)
    model_name = (
        f"SARIMA{order_label}{seasonal_label}"
        if candidate.model_name == "SARIMA" else
        f"ARIMA{order_label}"
    )

    results = []

    for index in range(forecast_days):
        predicted_views = safe_positive_int(predicted_values[index])
        lower_bound = safe_positive_int(lower_values[index])
        upper_bound = max(predicted_views, safe_positive_int(upper_values[index]))

        results.append({
            "prediction_date": last_date + timedelta(days=index + 1),
            "predicted_views": predicted_views,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "model_name": model_name,
            "arima_order": order_label,
            "seasonal_order": seasonal_label if candidate.model_name == "SARIMA" else "",
            "mae": candidate.mae,
            "rmse": candidate.rmse,
            "mape": candidate.mape,
            "wmape": candidate.wmape,
            "smape": candidate.smape,
            "aic": safe_float(model.aic),
            "bic": safe_float(model.bic),
        })

    return results


def forecast_with_best_model(series, forecast_days=DEFAULT_FORECAST_DAYS, fast=False):
    forecast_days = normalize_forecast_days(forecast_days)

    if series is None or series.empty:
        return []

    profile = profile_series(series)
    fallback_candidate = evaluate_moving_average_baseline(series, forecast_days)

    if not is_arima_eligible(profile):
        return build_fallback_results(
            series,
            forecast_days,
            fallback_candidate,
            reason="data_terbatas",
        )

    arima_candidate = find_best_arima_model(series, forecast_days, fast=fast)

    if should_use_fallback(arima_candidate, fallback_candidate):
        return build_fallback_results(
            series,
            forecast_days,
            fallback_candidate,
            reason="baseline_lebih_stabil",
        )

    try:
        results = build_model_results(series, arima_candidate, forecast_days)
    except Exception:
        return build_fallback_results(
            series,
            forecast_days,
            fallback_candidate,
            reason="arima_final_error",
        )

    if not results:
        return build_fallback_results(
            series,
            forecast_days,
            fallback_candidate,
            reason="arima_tidak_valid",
        )

    return results


def run_arima(series, forecast_days=DEFAULT_FORECAST_DAYS):
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


def build_prediction_objects_for_category(
    category,
    forecast_days=DEFAULT_FORECAST_DAYS,
    forecast_run=None,
    fast=False,
):
    series = prepare_time_series(
        category=category,
        end_date=get_latest_traffic_date(),
    )
    forecast_results = forecast_with_best_model(
        series=series,
        forecast_days=forecast_days,
        fast=fast,
    )

    return [
        Prediction(**build_prediction_kwargs(category, item, forecast_run))
        for item in forecast_results
    ]


def generate_forecast_for_category(
    category,
    forecast_days=DEFAULT_FORECAST_DAYS,
    forecast_run=None,
    fast=False,
):
    forecast_days = normalize_forecast_days(forecast_days)
    prediction_objects = build_prediction_objects_for_category(
        category=category,
        forecast_days=forecast_days,
        forecast_run=forecast_run,
        fast=fast,
    )

    with transaction.atomic():
        Prediction.objects.filter(category=category).delete()

        if prediction_objects:
            Prediction.objects.bulk_create(prediction_objects, batch_size=500)

    return len(prediction_objects)


def get_categories_for_forecast(category=None):
    queryset = Category.objects.all().order_by("name")

    if category in [None, ""]:
        return list(queryset)

    category_value = str(category).strip()

    if category_value.isdigit():
        return list(queryset.filter(id=int(category_value)))

    return list(queryset.filter(slug=category_value))


def cleanup_old_forecast_runs(keep_last=10):
    keep_last = normalize_history_limit(keep_last)
    kept_ids = list(
        ForecastRun.objects
        .order_by("-started_at", "-id")
        .values_list("id", flat=True)[:keep_last]
    )

    if not kept_ids:
        return 0

    deleted_count, _ = ForecastRun.objects.exclude(id__in=kept_ids).delete()

    return deleted_count


def generate_all_forecasts(
    forecast_days=DEFAULT_FORECAST_DAYS,
    forecast_run=None,
    category=None,
    fast=False,
):
    forecast_days = normalize_forecast_days(forecast_days)
    categories = get_categories_for_forecast(category)
    prediction_objects = []
    failed_categories = []
    fallback_categories = 0
    wmape_values = []

    for category_obj in categories:
        try:
            category_predictions = build_prediction_objects_for_category(
                category=category_obj,
                forecast_days=forecast_days,
                forecast_run=forecast_run,
                fast=fast,
            )
            prediction_objects.extend(category_predictions)

            if category_predictions:
                first_prediction = category_predictions[0]
                model_name = (first_prediction.model_name or "").lower()

                if "moving" in model_name or "fallback" in model_name:
                    fallback_categories += 1

                if first_prediction.wmape is not None:
                    wmape_values.append(first_prediction.wmape)
        except Exception as error:
            failed_categories.append(f"{category_obj.name}: {error}")

    with transaction.atomic():
        if categories:
            Prediction.objects.filter(category__in=categories).delete()

        if prediction_objects:
            Prediction.objects.bulk_create(prediction_objects, batch_size=500)

    average_wmape = safe_float(np.mean(wmape_values)) if wmape_values else None

    return ForecastSummary(
        total_categories=len(categories),
        total_predictions=len(prediction_objects),
        successful_categories=len(categories) - len(failed_categories),
        fallback_categories=fallback_categories,
        failed_categories=failed_categories,
        average_wmape=average_wmape,
        forecast_days=forecast_days,
    )


def update_forecast_run_success(forecast_run, summary):
    forecast_run_fields = get_model_field_names(ForecastRun)
    partial_status = getattr(ForecastRun, "STATUS_PARTIAL", "partial")
    success_status = getattr(ForecastRun, "STATUS_SUCCESS", "success")

    if "status" in forecast_run_fields:
        forecast_run.status = partial_status if summary.failed_categories else success_status

    if "forecast_days" in forecast_run_fields:
        forecast_run.forecast_days = summary.forecast_days

    if "total_predictions" in forecast_run_fields:
        forecast_run.total_predictions = summary.total_predictions

    if "finished_at" in forecast_run_fields:
        forecast_run.finished_at = timezone.now()

    if "error_message" in forecast_run_fields:
        forecast_run.error_message = " | ".join(summary.failed_categories)[:2000]

    forecast_run.save()


def create_forecast_run_and_generate(
    forecast_days=DEFAULT_FORECAST_DAYS,
    category=None,
    fast=False,
):
    forecast_days = normalize_forecast_days(forecast_days)
    forecast_run_fields = get_model_field_names(ForecastRun)
    running_status = getattr(ForecastRun, "STATUS_RUNNING", "running")
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
            category=category,
            fast=fast,
        )
        update_forecast_run_success(forecast_run, summary)
        forecast_run.summary = summary
    except Exception as error:
        if "status" in forecast_run_fields:
            forecast_run.status = failed_status

        if "error_message" in forecast_run_fields:
            forecast_run.error_message = str(error)[:2000]

        if "finished_at" in forecast_run_fields:
            forecast_run.finished_at = timezone.now()

        forecast_run.save()
        raise
    finally:
        cleanup_old_forecast_runs(
            keep_last=getattr(settings, "FORECAST_HISTORY_LIMIT", 10)
        )

    return forecast_run
