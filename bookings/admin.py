from django.contrib import admin
from .models import (
    Booking,
    BookingParticipant,
    ClientCard,
    Review,
    TimeSlot,
    WaitlistEntry,
)


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('box', 'date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'date', 'box__service')
    list_editable = ('status',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'slot', 'offering', 'employee', 'status', 'created_at')
    list_filter = ('status', 'offering', 'employee')
    search_fields = ('user__username',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'rating', 'is_approved', 'created_at')
    list_filter = ('rating', 'service', 'is_approved')
    list_editable = ('is_approved',)


admin.site.register(WaitlistEntry)
admin.site.register(ClientCard)
admin.site.register(BookingParticipant)
