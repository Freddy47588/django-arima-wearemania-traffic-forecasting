import csv
from datetime import datetime

from django.core.management.base import BaseCommand
from analytics.models import Category, TrafficData


class Command(BaseCommand):
    help = "Import cleaned daily category CSV into TrafficData"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to cleaned_daily_category.csv")

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        self.stdout.write(self.style.WARNING(f"Mulai import file: {csv_file}"))

        with open(csv_file, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            required_columns = {"date", "category", "views"}

            if not required_columns.issubset(reader.fieldnames):
                self.stdout.write(
                    self.style.ERROR(
                        f"Format CSV salah. Kolom wajib: {required_columns}. "
                        f"Kolom ditemukan: {reader.fieldnames}"
                    )
                )
                return

            for row in reader:
                try:
                    date_value = row["date"].strip()
                    category_name = row["category"].strip()
                    views_value = row["views"].strip()

                    date = datetime.strptime(date_value, "%Y-%m-%d").date()
                    views = int(float(views_value))

                    if not category_name:
                        skipped_count += 1
                        continue

                    category, _ = Category.objects.get_or_create(
                        name=category_name
                    )

                    _, created = TrafficData.objects.update_or_create(
                        category=category,
                        date=date,
                        defaults={
                            "views": views
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Baris dilewati: {row} | Error: {e}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS("Import selesai."))
        self.stdout.write(f"Data baru   : {created_count}")
        self.stdout.write(f"Data update : {updated_count}")
        self.stdout.write(f"Data gagal  : {skipped_count}")