from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from datetime import datetime, timedelta
import requests
from .models import TimeSlot, Booking, Review
from services.models import Box, Service

TELEGRAM_TOKEN = '8929399215:AAHzdtEOK-qSMfa3IBsprjJM22Os5N8kG0E'
ADMIN_CHAT_ID = '316023355'


def send_telegram_notification(service, message):
    chat_id = service.telegram_chat_id if service.telegram_chat_id else ADMIN_CHAT_ID
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        requests.post(url, data={'chat_id': chat_id, 'text': message})
    except Exception as e:
        print(f'Telegram error: {e}')


def slot_list(request, box_id):
    box = get_object_or_404(Box, pk=box_id, is_active=True)
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    slots = TimeSlot.objects.filter(box=box).filter(
        models.Q(date__gt=today) | models.Q(date=today, start_time__gte=current_time)
    ).order_by('date', 'start_time')

    return render(request, 'bookings/slot_list.html', {
        'box': box,
        'slots': slots,
    })


@login_required
def book_slot(request, slot_id):
    slot = get_object_or_404(TimeSlot, pk=slot_id, status='free')
    is_owner = request.user.role == 'business_owner'

    if request.method == 'POST':
        slot.status = 'booked'
        slot.save()
        if is_owner:
            client_name = request.POST.get('client_name', '')
            client_phone = request.POST.get('client_phone', '')
            Booking.objects.create(
                slot=slot,
                client_name=client_name,
                client_phone=client_phone,
            )
            send_telegram_notification(slot.box.service,
                f"📞 Новая бронь по звонку!\n"
                f"Сервис: {slot.box.service.name}\n"
                f"{slot.box.name}\n"
                f"Клиент: {client_name} ({client_phone})\n"
                f"Дата: {slot.date} {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"
            )
            messages.success(request, 'Слот забронирован за клиентом!')
            return redirect('owner_dashboard', service_id=slot.box.service.pk)
        else:
            Booking.objects.create(user=request.user, slot=slot)
            send_telegram_notification(slot.box.service,
                f"🎉 Новая онлайн-бронь!\n"
                f"Сервис: {slot.box.service.name}\n"
                f"{slot.box.name}\n"
                f"Клиент: {request.user.username} ({request.user.phone})\n"
                f"Дата: {slot.date} {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"
            )
            messages.success(request, 'Вы успешно забронировали слот!')
            return redirect('my_bookings')

    return render(request, 'bookings/book_slot.html', {
        'slot': slot,
        'is_owner': is_owner,
    })


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'bookings/my_bookings.html', {'bookings': bookings})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    if request.method == 'POST':
        booking.slot.status = 'free'
        booking.slot.save()
        booking.delete()
        messages.success(request, 'Бронирование отменено.')
        return redirect('my_bookings')
    return render(request, 'bookings/cancel_booking.html', {'booking': booking})


@login_required
def owner_dashboard(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    bookings = Booking.objects.filter(
        slot__box__service=service
    ).exclude(slot__status='free').order_by('slot__date', 'slot__start_time')
    total_bookings = bookings.count()
    in_progress = bookings.filter(slot__status='in_progress').count()
    free_slots = TimeSlot.objects.filter(box__service=service, status='free').count()
    return render(request, 'bookings/owner_dashboard.html', {
        'service': service,
        'bookings': bookings,
        'total_bookings': total_bookings,
        'in_progress': in_progress,
        'free_slots': free_slots,
    })


@login_required
def slot_in_progress(request, slot_id):
    slot = get_object_or_404(TimeSlot, pk=slot_id)
    if request.method == 'POST':
        slot.status = 'in_progress'
        slot.save()
    return redirect('owner_dashboard', service_id=slot.box.service.pk)


@login_required
def slot_free(request, slot_id):
    slot = get_object_or_404(TimeSlot, pk=slot_id)
    if request.method == 'POST':
        slot.status = 'free'
        slot.save()
        Booking.objects.filter(slot=slot).delete()
    return redirect('owner_dashboard', service_id=slot.box.service.pk)


@login_required
def generate_slots(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')

    if request.method == 'POST':
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        interval = int(request.POST.get('interval', 60))
        boxes = service.boxes.filter(is_active=True)

        start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_date = datetime.strptime(date_to, "%Y-%m-%d").date()

        count = 0
        current_date = start_date
        while current_date <= end_date:
            start = datetime.strptime(f"{current_date} {service.opening_time}", "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(f"{current_date} {service.closing_time}", "%Y-%m-%d %H:%M:%S")

            for box in boxes:
                current = start
                while current + timedelta(minutes=interval) <= end:
                    slot_end = current + timedelta(minutes=interval)
                    _, created = TimeSlot.objects.get_or_create(
                        box=box,
                        date=current_date,
                        start_time=current.time(),
                        end_time=slot_end.time(),
                        defaults={'status': 'free'}
                    )
                    if created:
                        count += 1
                    current = slot_end
            current_date += timedelta(days=1)

        messages.success(request, f'Создано {count} слотов с {date_from} по {date_to}!')
        return redirect('owner_dashboard', service_id=service.pk)

    return render(request, 'bookings/generate_slots.html', {'service': service})


@login_required
def delete_slots(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')

    if request.method == 'POST':
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        time_from = request.POST.get('time_from')
        time_to = request.POST.get('time_to')

        slots = TimeSlot.objects.filter(
            box__service=service,
            status='free'
        )

        if date_from:
            slots = slots.filter(date__gte=date_from)
        if date_to:
            slots = slots.filter(date__lte=date_to)
        if time_from:
            slots = slots.filter(start_time__gte=time_from)
        if time_to:
            slots = slots.filter(end_time__lte=time_to)

        deleted, _ = slots.delete()
        messages.success(request, f'Удалено {deleted} свободных слотов.')
        return redirect('owner_dashboard', service_id=service.pk)

    return render(request, 'bookings/delete_slots.html', {'service': service})


@login_required
def add_review(request, service_id):
    service = get_object_or_404(Service, pk=service_id)

    has_booking = Booking.objects.filter(
        user=request.user,
        slot__box__service=service,
        slot__status='free'
    ).exists()

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if rating and comment:
            Review.objects.update_or_create(
                user=request.user,
                service=service,
                defaults={'rating': rating, 'comment': comment}
            )
            messages.success(request, 'Отзыв оставлен!')
        return redirect('service_detail', pk=service.pk)

    return render(request, 'bookings/add_review.html', {
        'service': service,
        'has_booking': has_booking,
    })


@login_required
def connect_telegram(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')

    if request.method == 'POST':
        from .telegram_bot import process_updates
        process_updates()
        service.refresh_from_db()
        if service.telegram_chat_id:
            messages.success(request, 'Telegram подключён!')
        else:
            messages.error(request, 'Не удалось найти подключение. Убедитесь что отправили команду боту.')
        return redirect('owner_dashboard', service_id=service.pk)

    return render(request, 'bookings/connect_telegram.html', {'service': service})