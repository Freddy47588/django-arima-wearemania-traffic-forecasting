from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TrafficData(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="traffic_data"
    )
    date = models.DateField()
    page_path = models.TextField(blank=True, null=True)
    views = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["category", "date"]),
        ]
        verbose_name = "Traffic Data"
        verbose_name_plural = "Traffic Data"

    def __str__(self):
        return f"{self.category.name} - {self.date} - {self.views} views"


class ForecastRun(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    forecast_days = models.PositiveIntegerField(default=7)
    total_predictions = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True, null=True)

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Forecast Run"
        verbose_name_plural = "Forecast Runs"

    def mark_success(self, total_predictions=0):
        self.status = self.STATUS_SUCCESS
        self.total_predictions = total_predictions
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "total_predictions", "finished_at"])

    def mark_failed(self, error_message):
        self.status = self.STATUS_FAILED
        self.error_message = str(error_message)
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finished_at"])

    def __str__(self):
        return f"ForecastRun #{self.id} - {self.status}"


class Prediction(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="predictions"
    )
    forecast_run = models.ForeignKey(
        ForecastRun,
        on_delete=models.SET_NULL,
        related_name="predictions",
        blank=True,
        null=True
    )

    prediction_date = models.DateField()
    predicted_views = models.PositiveIntegerField(default=0)
    lower_bound = models.PositiveIntegerField(default=0)
    upper_bound = models.PositiveIntegerField(default=0)

    model_name = models.CharField(max_length=100, default="ARIMA")
    arima_order = models.CharField(max_length=30, blank=True, null=True)
    seasonal_order = models.CharField(max_length=40, blank=True, null=True)
    mae = models.FloatField(blank=True, null=True)
    rmse = models.FloatField(blank=True, null=True)
    mape = models.FloatField(blank=True, null=True)
    aic = models.FloatField(blank=True, null=True)
    bic = models.FloatField(blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["prediction_date"]
        indexes = [
            models.Index(fields=["prediction_date"]),
            models.Index(fields=["category", "prediction_date"]),
        ]
        verbose_name = "Prediction"
        verbose_name_plural = "Predictions"

    def __str__(self):
        return (
            f"{self.category.name} - "
            f"{self.prediction_date} - "
            f"{self.predicted_views} predicted views"
        )
