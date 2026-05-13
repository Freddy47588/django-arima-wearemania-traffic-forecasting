from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class TrafficData(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    date = models.DateField()
    views = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("category", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} - {self.category.name} - {self.views}"
class Prediction(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    prediction_date = models.DateField()
    predicted_views = models.FloatField()
    lower_bound = models.FloatField(null=True, blank=True)
    upper_bound = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
class ImportLog(models.Model):
    file_name = models.CharField(max_length=255)
    total_rows = models.IntegerField(default=0)
    cleaned_rows = models.IntegerField(default=0)
    skipped_rows = models.IntegerField(default=0)
    imported_rows = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="success")
    message = models.TextField(blank=True, null=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} - {self.status}"