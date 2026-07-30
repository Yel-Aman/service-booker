from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('client', 'Клиент'),
        ('business_owner', 'Владелец бизнеса'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    business_name = models.CharField(max_length=200, blank=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True)
    favorites = models.ManyToManyField('services.Service', blank=True, related_name='favorited_by')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_business_owner(self):
        return self.role == 'business_owner'

    @property
    def no_show_count(self):
        return self.booking_set.filter(status='no_show').count()

class RecentlyViewedService(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='recently_viewed',
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='recent_views',
    )
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'service'],
                name='unique_recent_service_per_user',
            ),
        ]


class UserDailyActivity(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='daily_activity',
    )
    date = models.DateField()
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date'],
                name='unique_user_activity_per_day',
            ),
        ]
