from django.core.management.base import BaseCommand, CommandError

from analytics.services.csv_importer import BATCH_SIZE, import_daily_category_csv


class Command(BaseCommand):
    help = "Import cleaned daily category CSV into TrafficData"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to cleaned_daily_category.csv")

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        self.stdout.write(self.style.WARNING(f"Mulai import file: {csv_file}"))
        self.stdout.write(f"Batch insert size: {BATCH_SIZE}")

        try:
            with open(csv_file, newline="", encoding="utf-8") as file:
                result = import_daily_category_csv(file)
        except FileNotFoundError as error:
            raise CommandError(f"File tidak ditemukan: {csv_file}") from error
        except ValueError as error:
            raise CommandError(str(error)) from error
        except Exception as error:
            raise CommandError(f"Gagal memproses CSV: {error}") from error

        self.stdout.write(self.style.SUCCESS("Import selesai."))
        self.stdout.write(f"Row diproses       : {result.processed_rows}")
        self.stdout.write(f"Row valid          : {result.valid_rows}")
        self.stdout.write(f"Data baru          : {result.created_count}")
        self.stdout.write(f"Duplikat file      : {result.duplicate_in_file_count}")
        self.stdout.write(f"Duplikat database  : {result.duplicate_in_database_count}")
        self.stdout.write(f"Data gagal/skip    : {result.skipped_count}")
        self.stdout.write(f"Periode tanggal    : {result.first_date} - {result.last_date}")
        self.stdout.write(f"Total kategori     : {result.total_categories}")
