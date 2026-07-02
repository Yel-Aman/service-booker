from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    slot_unit = models.CharField(max_length=50, default='Бокс')
    image_url = models.URLField(blank=True, help_text='Ссылка на картинку с Unsplash или другого сайта')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"