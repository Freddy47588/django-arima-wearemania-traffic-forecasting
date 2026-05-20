from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "category"
            slug = base_slug
            counter = 2

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

    def __str__(self):
        return f"{self.category.name} - {self.date} - {self.views} views"


class ForecastRun(models.Model):
    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    model_name = models.CharField(max_length=100, default="ARIMA")
    forecast_days = models.PositiveIntegerField(default=7)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="running"
    )
    total_predictions = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.model_name} - {self.status} - {self.created_at}"


class Prediction(models.Model):
    forecast_run = models.ForeignKey(
        ForecastRun,
        on_delete=models.CASCADE,
        related_name="predictions",
        blank=True,
        null=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="predictions"
    )
    prediction_date = models.DateField()
    predicted_views = models.PositiveIntegerField(default=0)
    lower_bound = models.PositiveIntegerField(default=0)
    upper_bound = models.PositiveIntegerField(default=0)
    model_order = models.CharField(max_length=50, default="ARIMA(1,1,1)")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["prediction_date"]
        indexes = [
            models.Index(fields=["category", "prediction_date"]),
        ]

    def __str__(self):
        return f"{self.category.name} - {self.prediction_date} - {self.predicted_views}"


class ImportLog(models.Model):
    filename = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    skipped_rows = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=50, default="success")
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} - {self.status}"