from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="prediction",
            name="aic",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prediction",
            name="arima_order",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="prediction",
            name="bic",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prediction",
            name="mae",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prediction",
            name="mape",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prediction",
            name="rmse",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prediction",
            name="seasonal_order",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
    ]
