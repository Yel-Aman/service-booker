from django.contrib import admin
from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name', 'is_active')
    list_editable = ('is_active',)