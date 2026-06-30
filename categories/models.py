from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    slot_unit = models.CharField(max_length=50, default='Бокс')  # Бокс, Кресло, Кабинет и т.д.

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"