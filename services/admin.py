from django.contrib import admin
from .models import Service, Box


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