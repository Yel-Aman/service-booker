from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('client', 'Клиент'),
        ('business_owner', 'Владелец бизнеса'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True)  # Телефон (WhatsApp/звонки)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    business_name = models.CharField(max_length=200, blank=True)  # Только для владельцев

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_business_owner(self):
        return self.role == 'business_owner'