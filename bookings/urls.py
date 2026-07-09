from django.urls import path
from . import views

urlpatterns = [
    path('box/<int:box_id>/', views.slot_list, name='slot_list'),
    path('book/<int:slot_id>/', views.book_slot, name='book_slot'),
    path('my/', views.my_bookings, name='my_bookings'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('dashboard/<int:service_id>/', views.owner_dashboard, name='owner_dashboard'),
    path('slot/progress/<int:slot_id>/', views.slot_in_progress, name='slot_in_progress'),
    path('slot/free/<int:slot_id>/', views.slot_free, name='slot_free'),
    path('generate/<int:service_id>/', views.generate_slots, name='generate_slots'),
    path('delete-slots/<int:service_id>/', views.delete_slots, name='delete_slots'),
    path('review/<int:service_id>/', views.add_review, name='add_review'),
    path('connect-telegram/<int:service_id>/', views.connect_telegram, name='connect_telegram'),
    path('analytics/<int:service_id>/', views.analytics, name='analytics'),
]