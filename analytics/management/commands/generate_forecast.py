from django.core.management.base import BaseCommand, CommandError

from analytics.models import TrafficData
from analytics.services.forecasting import (
    create_forecast_run_and_generate,
    normalize_forecast_days,
)


class Command(BaseCommand):
    help = "Generate ARIMA forecast for all traffic categories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Jumlah hari prediksi ke depan. Default: 7.",
        )

    def handle(self, *args, **options):
        forecast_days = normalize_forecast_days(options["days"])

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
                forecast_days=forecast_days
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Forecast generated successfully. "
                    f"Run ID: {forecast_run.id}. "
                    f"Total predictions: {forecast_run.total_predictions}."
                )
            )

        except Exception as error:
            raise CommandError(
                f"Forecast generation failed: {error}"
            )
