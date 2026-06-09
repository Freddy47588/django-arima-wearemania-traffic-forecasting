from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0003_prediction_wmape_smape"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="forecastrun",
            index=models.Index(
                fields=["started_at"],
                name="analytics_f_started_7b5f21_idx",
            ),
        ),
    ]
