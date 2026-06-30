from django.contrib import admin
from .models import Booking, TimeSlot, Review


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('box', 'date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'date', 'box__service')
    list_editable = ('status',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'slot', 'created_at')
    search_fields = ('user__username',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'rating', 'created_at')
    list_filter = ('rating', 'service')