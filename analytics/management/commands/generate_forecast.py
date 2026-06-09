from django.core.management.base import BaseCommand, CommandError
from django.db.models import Avg, Count

from analytics.models import Prediction, TrafficData
from analytics.services.forecasting import (
    MAX_FORECAST_DAYS,
    create_forecast_run_and_generate,
    normalize_forecast_days,
)


def format_metric(value, suffix=""):
    if value is None:
        return "n/a"

    return f"{value:.2f}{suffix}"


class Command(BaseCommand):
    help = "Generate ARIMA forecast for traffic categories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Jumlah hari prediksi ke depan. Default: 7, maksimal: 14.",
        )
        parser.add_argument(
            "--category",
            type=str,
            default=None,
            help="Opsional: ID atau slug kategori untuk generate satu kategori saja.",
        )
        parser.add_argument(
            "--fast",
            action="store_true",
            help="Lewati kandidat SARIMA musiman dan gunakan kandidat ARIMA kecil saja.",
        )

    def handle(self, *args, **options):
        requested_days = options["days"]
        forecast_days = normalize_forecast_days(requested_days)

        if requested_days > MAX_FORECAST_DAYS:
            self.stdout.write(
                self.style.WARNING(
                    "Forecast days dibatasi maksimal 14 hari agar prediksi tetap realistis."
                )
            )

        if not TrafficData.objects.exists():
            raise CommandError(
                "Data traffic belum tersedia. Upload CSV terlebih dahulu sebelum generate forecast."
            )

        self.stdout.write(
            self.style.WARNING(
                f"Generating forecast for {forecast_days} days..."
            )
        )

        try:
            forecast_run = create_forecast_run_and_generate(
                forecast_days=forecast_days,
                category=options["category"],
                fast=options["fast"],
            )

            predictions = Prediction.objects.filter(forecast_run=forecast_run)
            summary = predictions.aggregate(
                category_count=Count("category", distinct=True),
                avg_mae=Avg("mae"),
                avg_rmse=Avg("rmse"),
                avg_mape=Avg("mape"),
                avg_wmape=Avg("wmape"),
                avg_smape=Avg("smape"),
                avg_aic=Avg("aic"),
                avg_bic=Avg("bic"),
            )
            models = list(
                predictions
                .values_list("model_name", flat=True)
                .distinct()
                .order_by("model_name")
            )
            run_summary = getattr(forecast_run, "summary", None)
            fallback_count = getattr(run_summary, "fallback_categories", 0)
            failed_count = len(getattr(run_summary, "failed_categories", []) or [])
            success_count = getattr(
                run_summary,
                "successful_categories",
                summary["category_count"] or 0,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Forecast selesai. "
                    f"{success_count} kategori berhasil, "
                    f"{fallback_count} kategori fallback, "
                    f"{failed_count} kategori gagal. "
                    f"Periode prediksi: {forecast_days} hari. "
                    f"Run ID: {forecast_run.id}. "
                    f"Total prediksi: {forecast_run.total_predictions}."
                )
            )
            self.stdout.write(
                "Models: "
                f"{', '.join(models) if models else 'none'}"
            )
            self.stdout.write(
                "Best-run metrics average: "
                f"WMAPE={format_metric(summary['avg_wmape'], '%')}, "
                f"MAE={format_metric(summary['avg_mae'])}, "
                f"RMSE={format_metric(summary['avg_rmse'])}, "
                f"MAPE={format_metric(summary['avg_mape'], '%')}, "
                f"SMAPE={format_metric(summary['avg_smape'], '%')}, "
                f"AIC={format_metric(summary['avg_aic'])}, "
                f"BIC={format_metric(summary['avg_bic'])}."
            )

            if forecast_run.error_message:
                self.stdout.write(
                    self.style.WARNING(
                        f"Failed categories: {forecast_run.error_message}"
                    )
                )

        except Exception as error:
            raise CommandError(
                f"Forecast generation failed: {error}"
            )
