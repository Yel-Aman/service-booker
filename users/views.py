import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.db.models import Count
from django.utils import timezone
from bookings.models import Booking
from .forms import LoginForm, RegisterForm
from services.models import Service
from .models import CustomUser, RecentlyViewedService, UserDailyActivity
from config.throttling import is_rate_limited


def register(request):
    if request.method == 'POST':
        if is_rate_limited(request, 'register', 10, 3600):
            messages.error(request, 'Слишком много попыток. Попробуйте позже.')
            return render(request, 'users/register.html', {'form': RegisterForm()})
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Добро пожаловать!')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        if is_rate_limited(request, 'login', 20, 900):
            messages.error(request, 'Слишком много попыток входа. Попробуйте позже.')
            return render(request, 'users/login.html', {'form': LoginForm()})
        username = request.POST.get('username', '').lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Неверный логин или пароль')
        form = LoginForm(data=request.POST)
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    if request.method == 'POST':
        request.user.phone = request.POST.get('phone', request.user.phone)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        messages.success(request, 'Профиль обновлён!')
        return redirect('profile')
    return render(request, 'users/profile.html')


@login_required
def connect_client_telegram(request):
    if request.method == 'POST':
        from bookings.telegram_bot import process_updates
        process_updates()
        request.user.refresh_from_db()
        if request.user.telegram_chat_id:
            messages.success(request, 'Telegram подключён!')
        else:
            messages.error(request, 'Не удалось найти подключение.')
    return redirect('profile')


@login_required
def toggle_favorite(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    if service in request.user.favorites.all():
        request.user.favorites.remove(service)
        messages.success(request, f'"{service.name}" удалён из избранного.')
    else:
        request.user.favorites.add(service)
        messages.success(request, f'"{service.name}" добавлен в избранное!')
    return redirect('service_detail', pk=service_id)


@login_required
def favorites(request):
    services = request.user.favorites.all()
    return render(request, 'users/favorites.html', {'services': services})


@login_required
def recently_viewed(request):
    services = Service.objects.filter(
        recent_views__user=request.user,
    ).order_by('-recent_views__viewed_at')[:20]
    return render(request, 'users/recently_viewed.html', {'services': services})


@staff_member_required
def platform_dashboard(request):
    if not request.user.is_superuser:
        return redirect('home')

    today = timezone.localdate()
    start_7 = today - timedelta(days=6)
    start_30 = today - timedelta(days=29)
    users = CustomUser.objects.all()
    bookings = Booking.objects.select_related(
        'user',
        'slot__box__service__city',
        'slot__box__service__category',
    )

    activity_rows = {
        row['date']: row['count']
        for row in UserDailyActivity.objects.filter(
            date__gte=start_30,
        ).values('date').annotate(count=Count('user', distinct=True))
    }
    registration_rows = {
        row['day']: row['count']
        for row in users.filter(
            date_joined__date__gte=start_30,
        ).values(day=models.functions.TruncDate('date_joined')).annotate(
            count=Count('id')
        )
    }
    booking_rows = {
        row['day']: row['count']
        for row in bookings.filter(
            created_at__date__gte=start_30,
        ).values(day=models.functions.TruncDate('created_at')).annotate(
            count=Count('id')
        )
    }
    labels = [
        start_30 + timedelta(days=index)
        for index in range(30)
    ]
    chart_data = {
        'labels': [day.strftime('%d.%m') for day in labels],
        'activity': [activity_rows.get(day, 0) for day in labels],
        'registrations': [registration_rows.get(day, 0) for day in labels],
        'bookings': [booking_rows.get(day, 0) for day in labels],
    }

    recent_30_bookings = bookings.filter(slot__date__gte=start_30)
    return render(request, 'users/platform_dashboard.html', {
        'users_total': users.count(),
        'clients_total': users.filter(role='client').count(),
        'owners_total': users.filter(role='business_owner').count(),
        'new_today': users.filter(date_joined__date=today).count(),
        'new_7': users.filter(date_joined__date__gte=start_7).count(),
        'new_30': users.filter(date_joined__date__gte=start_30).count(),
        'dau': UserDailyActivity.objects.filter(date=today).count(),
        'wau': UserDailyActivity.objects.filter(
            date__gte=start_7,
        ).values('user_id').distinct().count(),
        'mau': UserDailyActivity.objects.filter(
            date__gte=start_30,
        ).values('user_id').distinct().count(),
        'services_total': Service.objects.count(),
        'active_services': Service.objects.filter(is_active=True).count(),
        'bookings_today': bookings.filter(created_at__date=today).count(),
        'appointments_today': bookings.filter(slot__date=today).count(),
        'completed_30': recent_30_bookings.filter(status='completed').count(),
        'cancelled_30': recent_30_bookings.filter(status='cancelled').count(),
        'no_show_30': recent_30_bookings.filter(status='no_show').count(),
        'top_services': recent_30_bookings.values(
            'slot__box__service__name',
            'slot__box__service__city__name_ru',
        ).annotate(count=Count('id')).order_by('-count')[:8],
        'top_categories': recent_30_bookings.values(
            'slot__box__service__category__name',
        ).annotate(count=Count('id')).order_by('-count')[:8],
        'top_cities': recent_30_bookings.values(
            'slot__box__service__city__name_ru',
        ).annotate(count=Count('id')).order_by('-count')[:8],
        'latest_users': users.order_by('-date_joined')[:8],
        'latest_bookings': bookings.order_by('-created_at')[:8],
        'chart_data': json.dumps(chart_data),
    })
