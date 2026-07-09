from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.service_list, name='service_list'),
    path('services/<int:pk>/', views.service_detail, name='service_detail'),
    path('map/', views.service_map, name='service_map'),
    path('services/<int:service_id>/edit/', views.edit_service, name='edit_service'),
    path('services/<int:service_id>/add-box/', views.add_box, name='add_box'),
    path('box/<int:box_id>/toggle/', views.toggle_box, name='toggle_box'),
    path('box/<int:box_id>/delete/', views.delete_box, name='delete_box'),
    path('box/<int:box_id>/edit/', views.edit_box, name='edit_box'),
]