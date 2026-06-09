from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0002_prediction_model_metrics"),
    ]

    operations = [
        migrations.AddField(
            model_name="prediction",
            name="smape",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prediction",
            name="wmape",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
