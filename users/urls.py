from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('connect-telegram/', views.connect_client_telegram, name='connect_client_telegram'),
    path('favorites/', views.favorites, name='favorites'),
    path('favorites/<int:service_id>/toggle/', views.toggle_favorite, name='toggle_favorite'),
]