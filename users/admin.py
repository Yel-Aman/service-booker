from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserDailyActivity


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Доп. информация', {'fields': ('role', 'phone', 'avatar', 'business_name')}),
    )


@admin.register(UserDailyActivity)
class UserDailyActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'last_seen_at')
    list_filter = ('date',)
    search_fields = ('user__username', 'user__email')
