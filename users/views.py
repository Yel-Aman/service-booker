from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm
from services.models import Service


def register(request):
    if request.method == 'POST':
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
        username = request.POST.get('username', '').lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Неверный логин или пароль')
        form = AuthenticationForm(data=request.POST)
    else:
        form = AuthenticationForm()
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