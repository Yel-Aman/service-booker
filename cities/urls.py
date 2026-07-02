from django.urls import path
from . import views

urlpatterns = [
    path('set-city/', views.set_city, name='set_city'),
]