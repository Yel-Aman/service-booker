import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
import json
from .models import Service, Box
from categories.models import Category
from cities.models import City
from cities.views import get_current_city


def home(request):
    current_city = get_current_city(request)
    categories = Category.objects.all()
    services = Service.objects.filter(is_active=True, city=current_city)[:6]
    return render(request, 'services/home.html', {
        'categories': categories,
        'services': services,
        'current_city': current_city,
    })


def service_list(request):
    current_city = get_current_city(request)
    services = Service.objects.filter(is_active=True, city=current_city)
    categories = Category.objects.all()

    category_id = request.GET.get('category')
    query = request.GET.get('q', '')
    open_now = request.GET.get('open_now')

    if category_id:
        services = services.filter(category_id=category_id)
    if query:
        services = (
            services.filter(name__icontains=query) |
            services.filter(address__icontains=query) |
            services.filter(description__icontains=query) |
            services.filter(category__name__icontains=query)
        ).distinct()
    if open_now:
        from datetime import datetime
        now = datetime.now().time()
        services = services.filter(opening_time__lte=now, closing_time__gte=now)

    return render(request, 'services/service_list.html', {
        'services': services,
        'categories': categories,
        'selected_category': category_id,
        'query': query,
        'open_now': open_now,
        'current_city': current_city,
    })


def service_detail(request, pk):
    service = get_object_or_404(Service, pk=pk, is_active=True)
    reviews = service.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
    return render(request, 'services/service_detail.html', {
        'service': service,
        'reviews': reviews,
        'avg_rating': avg_rating,
    })


def service_map(request):
    current_city = get_current_city(request)
    services = Service.objects.filter(is_active=True, city=current_city)
    services_data = []
    for s in services:
        services_data.append({
            'id': s.pk,
            'name': s.name,
            'address': s.address,
            'phone': s.phone,
            'category': s.category.name,
            'lat': float(s.latitude),
            'lng': float(s.longitude),
            'url': f'/services/{s.pk}/',
        })
    return render(request, 'services/map.html', {
        'services_json': json.dumps(services_data, ensure_ascii=False),
        'current_city': current_city,
    })


@login_required
def edit_service(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')

    if request.method == 'POST':
        service.name = request.POST.get('name', service.name)
        service.description = request.POST.get('description', service.description)
        service.address = request.POST.get('address', service.address)
        service.phone = request.POST.get('phone', service.phone)
        service.opening_time = request.POST.get('opening_time', service.opening_time)
        service.closing_time = request.POST.get('closing_time', service.closing_time)
        service.save()
        messages.success(request, 'Данные сервиса обновлены!')
        return redirect('owner_dashboard', service_id=service.pk)

    return render(request, 'services/edit_service.html', {'service': service})


@login_required
def add_box(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Box.objects.create(service=service, name=name)
            messages.success(request, f'"{name}" добавлен!')
        return redirect('owner_dashboard', service_id=service.pk)
    return redirect('owner_dashboard', service_id=service.pk)


@login_required
def toggle_box(request, box_id):
    box = get_object_or_404(Box, pk=box_id)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    if request.method == 'POST':
        box.is_active = not box.is_active
        box.save()
        status = 'активирован' if box.is_active else 'деактивирован'
        messages.success(request, f'"{box.name}" {status}.')
    return redirect('owner_dashboard', service_id=box.service.pk)


@login_required
def delete_box(request, box_id):
    box = get_object_or_404(Box, pk=box_id)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    if request.method == 'POST':
        service_id = box.service.pk
        box.delete()
        messages.success(request, 'Удалено!')
        return redirect('owner_dashboard', service_id=service_id)
    return redirect('owner_dashboard', service_id=box.service.pk)


@login_required
def edit_box(request, box_id):
    box = get_object_or_404(Box, pk=box_id)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            box.name = name
            box.save()
            messages.success(request, f'Переименовано в "{name}".')
    return redirect('owner_dashboard', service_id=box.service.pk)