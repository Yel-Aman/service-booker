from django.db import models
from django.conf import settings
from services.models import Employee, Service, ServiceOffering, Box


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
        constraints = [
            models.UniqueConstraint(
                fields=['box', 'date', 'start_time', 'end_time'],
                name='unique_time_slot',
            ),
        ]


class Booking(models.Model):
    CONFIRMATION_CHOICES = [
        ('pending', 'Ожидает ответа'),
        ('confirmed', 'Клиент придёт'),
        ('declined', 'Клиент не сможет прийти'),
    ]
    STATUS_CHOICES = [
        ('confirmed', 'Подтверждено'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
        ('no_show', 'Клиент не пришёл'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    offering = models.ForeignKey(
        ServiceOffering,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    client_name = models.CharField(max_length=100, blank=True)
    client_phone = models.CharField(max_length=20, blank=True)
    cancellation_reason = models.CharField(max_length=300, blank=True)
    owner_note = models.CharField(max_length=500, blank=True)
    no_show_marked_at = models.DateTimeField(null=True, blank=True)
    visit_confirmation = models.CharField(
        max_length=20,
        choices=CONFIRMATION_CHOICES,
        default='pending',
    )
    visit_confirmed_at = models.DateTimeField(null=True, blank=True)
    is_group_booking = models.BooleanField(default=False)
    party_size = models.PositiveSmallIntegerField(default=1)
    invite_code = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        editable=False,
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['slot'],
                condition=models.Q(status__in=['confirmed', 'in_progress']),
                name='unique_active_booking_per_slot',
            ),
        ]

    def __str__(self):
        if self.user:
            return f"{self.user} — {self.slot}"
        return f"{self.client_name} ({self.client_phone}) — {self.slot}"


class BookingParticipant(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='participants',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_booking_participations',
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['booking', 'user'],
                name='unique_group_booking_participant',
            ),
        ]


class WaitlistEntry(models.Model):
    STATUS_CHOICES = [
        ('active', 'Ожидает'),
        ('booked', 'Записался'),
        ('cancelled', 'Отменено'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='waitlist_entries',
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='waitlist_entries',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
    )
    note = models.CharField(max_length=300, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'service'],
                condition=models.Q(status='active'),
                name='unique_active_waitlist_entry',
            ),
        ]


class ClientCard(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='client_cards',
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='business_client_cards',
    )
    owner_note = models.TextField(blank=True)
    preferences = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['service', 'client'],
                name='unique_client_card_per_service',
            ),
        ]


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    owner_response = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'service')

    def __str__(self):
        return f"{self.user} — {self.service} — {self.rating}⭐"
