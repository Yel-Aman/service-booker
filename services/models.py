from django.db import models
from django.conf import settings
from categories.models import Category
from cities.models import City


class Service(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    description = models.TextField(blank=True)
    address = models.CharField(max_length=300)
    phone = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name


class Box(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='boxes')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.service.name} — {self.name}"

    class Meta:
        verbose_name_plural = "Boxes"