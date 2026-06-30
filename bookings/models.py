from django.db import models
from django.conf import settings
from services.models import Service, Box


class TimeSlot(models.Model):
    STATUS_CHOICES = [
        ('free', 'Свободно'),
        ('booked', 'Забронировано'),
        ('in_progress', 'В процессе'),
    ]

    box = models.ForeignKey(Box, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='free')

    def __str__(self):
        return f"{self.box} | {self.date} {self.start_time}-{self.end_time} | {self.get_status_display()}"

    class Meta:
        ordering = ['date', 'start_time']


class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    slot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    client_name = models.CharField(max_length=100, blank=True)
    client_phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        if self.user:
            return f"{self.user} — {self.slot}"
        return f"{self.client_name} ({self.client_phone}) — {self.slot}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'service')

    def __str__(self):
        return f"{self.user} — {self.service} — {self.rating}⭐"