from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
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
    website = models.URLField(blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)

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


class ServiceOffering(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='offerings',
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default=60)
    boxes = models.ManyToManyField(Box, blank=True, related_name='offerings')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['service', 'name'],
                name='unique_offering_name_per_service',
            ),
        ]

    def clean(self):
        if self.duration_minutes < 5 or self.duration_minutes > 1440:
            raise ValidationError('Длительность услуги должна быть от 5 минут до 24 часов.')

    def __str__(self):
        return f'{self.service.name} — {self.name}'


class Employee(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='employees',
    )
    name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    photo_url = models.URLField(blank=True)
    boxes = models.ManyToManyField(Box, blank=True, related_name='employees')
    offerings = models.ManyToManyField(
        ServiceOffering,
        blank=True,
        related_name='employees',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.service.name} — {self.name}'


class WeeklySchedule(models.Model):
    WEEKDAYS = [
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
        (5, 'Суббота'),
        (6, 'Воскресенье'),
    ]

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='weekly_schedules',
    )
    box = models.ForeignKey(
        Box,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='weekly_schedules',
        help_text='Оставьте пустым для общего графика бизнеса.',
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    is_working = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def clean(self):
        if self.box_id and self.box.service_id != self.service_id:
            raise ValidationError('Ресурс должен принадлежать выбранному бизнесу.')
        if self.is_working:
            if not self.start_time or not self.end_time:
                raise ValidationError('Для рабочего дня укажите время начала и окончания.')
            if self.start_time >= self.end_time:
                raise ValidationError('Время окончания должно быть позже времени начала.')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['service', 'weekday'],
                condition=models.Q(box__isnull=True),
                name='unique_service_weekly_schedule',
            ),
            models.UniqueConstraint(
                fields=['box', 'weekday'],
                condition=models.Q(box__isnull=False),
                name='unique_box_weekly_schedule',
            ),
        ]
        ordering = ['box_id', 'weekday']

    def __str__(self):
        scope = self.box.name if self.box else self.service.name
        return f'{scope}: {self.get_weekday_display()}'


class ScheduleBreak(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='schedule_breaks',
    )
    box = models.ForeignKey(
        Box,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='schedule_breaks',
        help_text='Оставьте пустым, чтобы перерыв действовал на весь бизнес.',
    )
    weekday = models.PositiveSmallIntegerField(choices=WeeklySchedule.WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    label = models.CharField(max_length=100, blank=True)

    def clean(self):
        if self.box_id and self.box.service_id != self.service_id:
            raise ValidationError('Ресурс должен принадлежать выбранному бизнесу.')
        if self.start_time >= self.end_time:
            raise ValidationError('Время окончания должно быть позже времени начала.')

    class Meta:
        ordering = ['weekday', 'start_time']

    def __str__(self):
        return self.label or f'{self.get_weekday_display()} {self.start_time}–{self.end_time}'


class ScheduleException(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='schedule_exceptions',
    )
    box = models.ForeignKey(
        Box,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='schedule_exceptions',
    )
    date = models.DateField()
    is_closed = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    label = models.CharField(max_length=120, blank=True)

    def clean(self):
        if self.box_id and self.box.service_id != self.service_id:
            raise ValidationError('Ресурс должен принадлежать выбранному бизнесу.')
        if not self.is_closed:
            if not self.start_time or not self.end_time:
                raise ValidationError('Укажите время работы для изменённого дня.')
            if self.start_time >= self.end_time:
                raise ValidationError('Время окончания должно быть позже начала.')

    class Meta:
        ordering = ['date', 'box_id']
        constraints = [
            models.UniqueConstraint(
                fields=['service', 'date'],
                condition=models.Q(box__isnull=True),
                name='unique_service_schedule_exception',
            ),
            models.UniqueConstraint(
                fields=['box', 'date'],
                condition=models.Q(box__isnull=False),
                name='unique_box_schedule_exception',
            ),
        ]

    def __str__(self):
        return self.label or f'{self.service.name}: {self.date}'
