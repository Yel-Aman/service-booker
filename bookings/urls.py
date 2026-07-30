from django.urls import path
from . import views

urlpatterns = [
    path('box/<int:box_id>/', views.slot_list, name='slot_list'),
    path('book/<int:slot_id>/', views.book_slot, name='book_slot'),
    path('my/', views.my_bookings, name='my_bookings'),
    path('booking/<int:booking_id>/confirm-visit/', views.confirm_visit, name='confirm_visit'),
    path('booking/<int:booking_id>/repeat/', views.repeat_booking, name='repeat_booking'),
    path('booking/<int:booking_id>/invite/', views.booking_invite, name='booking_invite'),
    path('join/<uuid:invite_code>/', views.join_group_booking, name='join_group_booking'),
    path('waitlist/<int:service_id>/join/', views.join_waitlist, name='join_waitlist'),
    path('waitlist/<int:service_id>/leave/', views.leave_waitlist, name='leave_waitlist'),
    path('client-card/<int:service_id>/<int:user_id>/', views.client_card, name='client_card'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('reschedule/<int:booking_id>/', views.reschedule_booking, name='reschedule_booking'),
    path('booking/<int:booking_id>/<str:status>/', views.owner_booking_status, name='owner_booking_status'),
    path('dashboard/<int:service_id>/', views.owner_dashboard, name='owner_dashboard'),
    path('slot/progress/<int:slot_id>/', views.slot_in_progress, name='slot_in_progress'),
    path('slot/free/<int:slot_id>/', views.slot_free, name='slot_free'),
    path('generate/<int:service_id>/', views.generate_slots, name='generate_slots'),
    path('delete-slots/<int:service_id>/', views.delete_slots, name='delete_slots'),
    path('review/<int:service_id>/', views.add_review, name='add_review'),
    path('review/<int:review_id>/respond/', views.respond_review, name='respond_review'),
    path('connect-telegram/<int:service_id>/', views.connect_telegram, name='connect_telegram'),
    path('analytics/<int:service_id>/', views.analytics, name='analytics'),
    path('no-shows/<int:service_id>/', views.no_show_report, name='no_show_report'),
]
