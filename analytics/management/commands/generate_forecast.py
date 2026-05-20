from django.core.management.base import BaseCommand

from analytics.services.forecasting import generate_all_forecasts


class Command(BaseCommand):
    help = "Generate ARIMA forecast for all traffic categories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to forecast. Default: 7"
        )

    def handle(self, *args, **options):
        forecast_days = options["days"]

        self.stdout.write(
            self.style.WARNING(
                f"Generating ARIMA forecast for {forecast_days} days..."
            )
        )

        forecast_run = generate_all_forecasts(forecast_days=forecast_days)

        if forecast_run.status == "success":
            self.stdout.write(
                self.style.SUCCESS(
                    f"Forecast success. Total predictions: {forecast_run.total_predictions}"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Forecast failed: {forecast_run.message}"
                )
            )