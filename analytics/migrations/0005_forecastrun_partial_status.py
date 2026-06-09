from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0004_forecastrun_started_at_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="forecastrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("running", "Running"),
                    ("success", "Success"),
                    ("partial", "Partial"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
