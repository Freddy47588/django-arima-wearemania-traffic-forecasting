from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class TrafficData(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    date = models.DateField()
    pageviews = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('category', 'date')

class Prediction(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    prediction_date = models.DateField()
    predicted_value = models.FloatField()
    lower_bound = models.FloatField(null=True, blank=True)
    upper_bound = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)