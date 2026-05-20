from django.core.management.base import BaseCommand

from analytics.services.forecasting import create_forecast_run_and_generate


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
        forecast_days = options["days"]

        if forecast_days < 1:
            forecast_days = 7

        if forecast_days > 30:
            forecast_days = 30

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
            self.stdout.write(
                self.style.ERROR(
                    f"Forecast generation failed: {error}"
                )
            )