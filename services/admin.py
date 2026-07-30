from django.contrib import admin
from .models import (
    Box,
    Employee,
    ScheduleBreak,
    ScheduleException,
    Service,
    ServiceOffering,
    WeeklySchedule,
)


class BoxInline(admin.TabularInline):
    model = Box
    extra = 1  # Показывает одну пустую строку для добавления


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'address', 'phone', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'address')
    inlines = [BoxInline]  # Боксы прямо внутри сервиса


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'is_active')
    list_filter = ('service', 'is_active')


@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ('service', 'box', 'weekday', 'is_working', 'start_time', 'end_time')
    list_filter = ('service', 'weekday', 'is_working')


@admin.register(ScheduleBreak)
class ScheduleBreakAdmin(admin.ModelAdmin):
    list_display = ('service', 'box', 'weekday', 'start_time', 'end_time', 'label')
    list_filter = ('service', 'weekday')


@admin.register(ServiceOffering)
class ServiceOfferingAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'price', 'duration_minutes', 'is_active')
    list_filter = ('service', 'is_active')
    search_fields = ('name', 'service__name')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'specialization', 'is_active')
    list_filter = ('service', 'is_active')
    search_fields = ('name', 'service__name')


@admin.register(ScheduleException)
class ScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = ('service', 'box', 'date', 'is_closed', 'start_time', 'end_time')
    list_filter = ('service', 'date', 'is_closed')
