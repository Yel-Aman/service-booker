import os
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.db import models
import json
from .models import (
    Box,
    Employee,
    ScheduleBreak,
    ScheduleException,
    Service,
    ServiceOffering,
    WeeklySchedule,
)
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
    show_all_cities = (
        request.user.is_authenticated
        and request.user.role == 'business_owner'
    )
    services = Service.objects.filter(is_active=True)
    if not show_all_cities:
        services = services.filter(city=current_city)
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
        'show_all_cities': show_all_cities,
    })


def service_detail(request, pk):
    service = get_object_or_404(Service, pk=pk, is_active=True)
    is_waitlisted = False
    if request.user.is_authenticated:
        from bookings.models import WaitlistEntry
        from users.models import RecentlyViewedService
        RecentlyViewedService.objects.update_or_create(
            user=request.user,
            service=service,
        )
        is_waitlisted = WaitlistEntry.objects.filter(
            user=request.user,
            service=service,
            status='active',
        ).exists()
    reviews = service.reviews.filter(is_approved=True).order_by('-created_at')
    avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
    return render(request, 'services/service_detail.html', {
        'service': service,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'offerings': service.offerings.filter(is_active=True),
        'employees': service.employees.filter(is_active=True),
        'is_waitlisted': is_waitlisted,
    })


def service_map(request):
    current_city = get_current_city(request)
    city_services = Service.objects.filter(
        is_active=True,
        city=current_city,
    ).select_related('category')
    category_id = request.GET.get('category', '').strip()
    service_id = request.GET.get('service', '').strip()
    query = request.GET.get('q', '').strip()
    has_filters = bool(category_id or service_id or query)

    services = city_services.none()
    if service_id:
        services = Service.objects.filter(
            pk=service_id,
            is_active=True,
        ).select_related('category', 'city')
        selected_service_object = services.first()
        if selected_service_object and selected_service_object.city:
            current_city = selected_service_object.city
    elif has_filters:
        services = city_services
        if category_id:
            services = services.filter(category_id=category_id)
        if query:
            services = services.filter(
                models.Q(name__icontains=query)
                | models.Q(address__icontains=query)
                | models.Q(category__name__icontains=query)
            )
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
        'services_data': services_data,
        'service_count': len(services_data),
        'current_city': current_city,
        'categories': Category.objects.all(),
        'city_services': city_services.order_by('name'),
        'selected_category': category_id,
        'selected_service': service_id,
        'query': query,
        'has_filters': has_filters,
        'city_center_json': json.dumps([
            float(current_city.latitude),
            float(current_city.longitude),
        ]),
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
        service.website = request.POST.get('website', '').strip()
        service.instagram = request.POST.get('instagram', '').strip()
        service.image_url = request.POST.get('image_url', '').strip()
        try:
            service.latitude = request.POST.get('latitude', service.latitude)
            service.longitude = request.POST.get('longitude', service.longitude)
            service.full_clean()
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
            return render(request, 'services/edit_service.html', {'service': service})
        service.save()
        messages.success(request, 'Данные сервиса обновлены!')
        return redirect('owner_dashboard', service_id=service.pk)

    return render(request, 'services/edit_service.html', {'service': service})


@login_required
def add_box(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
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
    box = get_object_or_404(Box, pk=box_id, service__owner=request.user)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    if request.method == 'POST':
        box.is_active = not box.is_active
        box.save()
        status = 'активирован' if box.is_active else 'деактивирован'
        messages.success(request, f'"{box.name}" {status}.')
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'is_active': box.is_active,
                'message': f'"{box.name}" {status}.',
            })
    return redirect('owner_dashboard', service_id=box.service.pk)


@login_required
def delete_box(request, box_id):
    box = get_object_or_404(Box, pk=box_id, service__owner=request.user)
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
    box = get_object_or_404(Box, pk=box_id, service__owner=request.user)
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


def _parse_time(value):
    return datetime.strptime(value, '%H:%M').time()


@login_required
def manage_schedule(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')

    selected_box = None
    selected_box_id = request.GET.get('box')
    if selected_box_id:
        selected_box = get_object_or_404(
            service.boxes,
            pk=selected_box_id,
        )

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'save_weekly':
                box_id = request.POST.get('box_id')
                box = (
                    get_object_or_404(service.boxes, pk=box_id)
                    if box_id else None
                )
                for weekday, _ in WeeklySchedule.WEEKDAYS:
                    is_working = request.POST.get(f'is_working_{weekday}') == 'on'
                    start_value = request.POST.get(f'start_time_{weekday}')
                    end_value = request.POST.get(f'end_time_{weekday}')
                    schedule, _ = WeeklySchedule.objects.get_or_create(
                        service=service,
                        box=box,
                        weekday=weekday,
                    )
                    schedule.is_working = is_working
                    schedule.start_time = _parse_time(start_value) if is_working else None
                    schedule.end_time = _parse_time(end_value) if is_working else None
                    schedule.full_clean()
                    schedule.save()
                messages.success(request, 'Недельный график сохранён.')
                suffix = f'?box={box.pk}' if box else ''
                return redirect(f"{reverse('manage_schedule', args=[service.pk])}{suffix}")

            if action == 'reset_box_schedule':
                box = get_object_or_404(
                    service.boxes,
                    pk=request.POST.get('box_id'),
                )
                box.weekly_schedules.all().delete()
                messages.success(
                    request,
                    f'{box.name} снова использует общий график бизнеса.',
                )
                return redirect(
                    f"{reverse('manage_schedule', args=[service.pk])}?box={box.pk}"
                )

            if action == 'add_break':
                box_id = request.POST.get('box_id')
                schedule_break = ScheduleBreak(
                    service=service,
                    box=(
                        get_object_or_404(service.boxes, pk=box_id)
                        if box_id else None
                    ),
                    weekday=int(request.POST['weekday']),
                    start_time=_parse_time(request.POST['start_time']),
                    end_time=_parse_time(request.POST['end_time']),
                    label=request.POST.get('label', '').strip(),
                )
                schedule_break.full_clean()
                schedule_break.save()
                messages.success(request, 'Перерыв добавлен.')
                return redirect('manage_schedule', service_id=service.pk)
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            if isinstance(error, ValidationError):
                error_text = ' '.join(error.messages)
            else:
                error_text = 'Проверьте заполненные даты и время.'
            messages.error(request, error_text)

    weekly_rows = []
    schedules = {
        row.weekday: row
        for row in service.weekly_schedules.filter(box=selected_box)
    }
    inherited_schedules = {}
    if selected_box:
        inherited_schedules = {
            row.weekday: row
            for row in service.weekly_schedules.filter(box__isnull=True)
        }
    for weekday, weekday_name in WeeklySchedule.WEEKDAYS:
        schedule = schedules.get(weekday) or inherited_schedules.get(weekday)
        weekly_rows.append({
            'weekday': weekday,
            'name': weekday_name,
            'is_working': schedule.is_working if schedule else True,
            'start_time': (
                schedule.start_time if schedule and schedule.start_time
                else service.opening_time
            ),
            'end_time': (
                schedule.end_time if schedule and schedule.end_time
                else service.closing_time
            ),
        })

    return render(request, 'services/manage_schedule.html', {
        'service': service,
        'selected_box': selected_box,
        'weekly_rows': weekly_rows,
        'weekdays': WeeklySchedule.WEEKDAYS,
        'breaks': service.schedule_breaks.select_related('box'),
    })


@login_required
def delete_schedule_break(request, break_id):
    schedule_break = get_object_or_404(
        ScheduleBreak,
        pk=break_id,
        service__owner=request.user,
    )
    service_id = schedule_break.service_id
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    if request.method == 'POST':
        schedule_break.delete()
        messages.success(request, 'Перерыв удалён.')
    return redirect('manage_schedule', service_id=service_id)


@login_required
def manage_catalog(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
    if request.user.role != 'business_owner':
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_offering':
                offering = ServiceOffering(
                    service=service,
                    name=request.POST.get('name', '').strip(),
                    description=request.POST.get('description', '').strip(),
                    price=request.POST.get('price'),
                    duration_minutes=int(request.POST.get('duration_minutes', 60)),
                )
                offering.full_clean()
                offering.save()
                offering.boxes.set(
                    service.boxes.filter(pk__in=request.POST.getlist('boxes'))
                )
                messages.success(request, 'Услуга добавлена.')
            elif action == 'add_employee':
                employee = Employee(
                    service=service,
                    name=request.POST.get('name', '').strip(),
                    specialization=request.POST.get('specialization', '').strip(),
                    phone=request.POST.get('phone', '').strip(),
                    photo_url=request.POST.get('photo_url', '').strip(),
                )
                employee.full_clean()
                employee.save()
                employee.boxes.set(
                    service.boxes.filter(pk__in=request.POST.getlist('boxes'))
                )
                employee.offerings.set(
                    service.offerings.filter(
                        pk__in=request.POST.getlist('offerings')
                    )
                )
                messages.success(request, 'Сотрудник добавлен.')
            elif action == 'add_exception':
                box_id = request.POST.get('box_id')
                is_closed = request.POST.get('is_closed') == 'on'
                exception = ScheduleException(
                    service=service,
                    box=get_object_or_404(service.boxes, pk=box_id) if box_id else None,
                    date=request.POST.get('date'),
                    is_closed=is_closed,
                    start_time=(
                        None if is_closed
                        else _parse_time(request.POST.get('start_time'))
                    ),
                    end_time=(
                        None if is_closed
                        else _parse_time(request.POST.get('end_time'))
                    ),
                    label=request.POST.get('label', '').strip(),
                )
                exception.full_clean()
                exception.save()
                messages.success(request, 'Исключение расписания добавлено.')
            return redirect('manage_catalog', service_id=service.pk)
        except (TypeError, ValueError, ValidationError) as error:
            error_text = (
                ' '.join(error.messages)
                if isinstance(error, ValidationError)
                else 'Проверьте заполненные поля.'
            )
            messages.error(request, error_text)

    return render(request, 'services/manage_catalog.html', {
        'service': service,
        'offerings': service.offerings.prefetch_related('boxes'),
        'employees': service.employees.prefetch_related('boxes', 'offerings'),
        'exceptions': service.schedule_exceptions.select_related('box'),
    })


@login_required
def delete_catalog_item(request, kind, item_id):
    model_map = {
        'offering': ServiceOffering,
        'employee': Employee,
        'exception': ScheduleException,
    }
    model = model_map.get(kind)
    if not model:
        return redirect('home')
    item = get_object_or_404(
        model,
        pk=item_id,
        service__owner=request.user,
    )
    service_id = item.service_id
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Удалено.')
    return redirect('manage_catalog', service_id=service_id)
