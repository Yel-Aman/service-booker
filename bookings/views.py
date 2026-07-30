import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError, models, transaction
from django.db.models import Count, Avg
from datetime import datetime, timedelta, date as date_type
import requests
from .models import TimeSlot, Booking, Review
from services.models import (
    Box,
    Employee,
    ScheduleBreak,
    ScheduleException,
    Service,
    ServiceOffering,
    WeeklySchedule,
)
from config.throttling import is_rate_limited

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_CHAT_ID = os.environ.get('TELEGRAM_ADMIN_CHAT_ID')


def send_telegram_notification(service, message):
    chat_id = service.telegram_chat_id if service.telegram_chat_id else ADMIN_CHAT_ID
    if not TELEGRAM_TOKEN or not chat_id:
        return
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        requests.post(url, data={'chat_id': chat_id, 'text': message}, timeout=5)
    except Exception as e:
        print(f'Telegram error: {e}')


def send_telegram_to_user(user, message):
    """Отправляет уведомление клиенту если он подключил Telegram"""
    if not user.telegram_chat_id:
        return
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        requests.post(url, data={'chat_id': user.telegram_chat_id, 'text': message}, timeout=5)
    except Exception as e:
        print(f'Telegram client error: {e}')


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
    is_owner = (
        request.user.role == 'business_owner'
        and slot.box.service.owner_id == request.user.id
    )

    if request.method == 'POST':
        if is_rate_limited(request, 'booking', 30, 600):
            messages.error(request, 'Слишком много операций. Попробуйте немного позже.')
            return redirect('slot_list', box_id=slot.box_id)
        offering = None
        employee = None
        offering_id = request.POST.get('offering')
        employee_id = request.POST.get('employee')
        if offering_id:
            offering = get_object_or_404(
                ServiceOffering,
                pk=offering_id,
                service=slot.box.service,
                is_active=True,
            )
        if employee_id:
            employee = get_object_or_404(
                Employee,
                pk=employee_id,
                service=slot.box.service,
                is_active=True,
            )
        try:
            with transaction.atomic():
                locked_slot = TimeSlot.objects.select_for_update().get(pk=slot.pk)
                if locked_slot.status != 'free' or Booking.objects.filter(
                    slot=locked_slot,
                    status__in=['confirmed', 'in_progress'],
                ).exists():
                    messages.error(request, 'Этот слот уже забронирован.')
                    return redirect('slot_list', box_id=slot.box_id)
                locked_slot.status = 'booked'
                locked_slot.save(update_fields=['status'])
                booking = Booking.objects.create(
                    user=None if is_owner else request.user,
                    slot=locked_slot,
                    offering=offering,
                    employee=employee,
                    notes=request.POST.get('notes', '').strip(),
                    client_name=request.POST.get('client_name', '') if is_owner else '',
                    client_phone=request.POST.get('client_phone', '') if is_owner else '',
                )
                slot = locked_slot
        except (IntegrityError, TimeSlot.DoesNotExist):
            messages.error(request, 'Этот слот только что забронировал другой клиент.')
            return redirect('slot_list', box_id=slot.box_id)

        if is_owner:
            client_name = booking.client_name
            client_phone = booking.client_phone
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
            # Уведомление владельцу
            send_telegram_notification(slot.box.service,
                f"🎉 Новая онлайн-бронь!\n"
                f"Сервис: {slot.box.service.name}\n"
                f"{slot.box.name}\n"
                f"Клиент: {request.user.username} ({request.user.phone})\n"
                f"Дата: {slot.date} {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"
            )
            # Уведомление клиенту
            send_telegram_to_user(request.user,
                f"✅ Вы записались!\n"
                f"Сервис: {slot.box.service.name}\n"
                f"{slot.box.name}\n"
                f"Дата: {slot.date} {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}\n"
                f"Адрес: {slot.box.service.address}"
            )
            messages.success(request, 'Вы успешно забронировали слот!')
            return redirect('my_bookings')

    return render(request, 'bookings/book_slot.html', {
        'slot': slot,
        'is_owner': is_owner,
        'offerings': slot.box.offerings.filter(is_active=True),
        'employees': slot.box.employees.filter(is_active=True),
    })


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'bookings/my_bookings.html', {'bookings': bookings})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(
        Booking,
        pk=booking_id,
        user=request.user,
        status__in=['confirmed', 'in_progress'],
    )
    if request.method == 'POST':
        # Уведомление клиенту об отмене
        send_telegram_to_user(request.user,
            f"❌ Бронирование отменено\n"
            f"Сервис: {booking.slot.box.service.name}\n"
            f"Дата: {booking.slot.date} {booking.slot.start_time.strftime('%H:%M')}"
        )
        booking.slot.status = 'free'
        booking.slot.save(update_fields=['status'])
        booking.status = 'cancelled'
        booking.cancellation_reason = request.POST.get('reason', '').strip()
        booking.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
        messages.success(request, 'Бронирование отменено.')
        return redirect('my_bookings')
    return render(request, 'bookings/cancel_booking.html', {'booking': booking})


@login_required
def reschedule_booking(request, booking_id):
    booking = get_object_or_404(
        Booking,
        pk=booking_id,
        user=request.user,
        status='confirmed',
    )
    service = booking.slot.box.service
    available_slots = TimeSlot.objects.filter(
        box__service=service,
        box__is_active=True,
        status='free',
        date__gte=date_type.today(),
    ).select_related('box').order_by('date', 'start_time')[:100]

    if request.method == 'POST':
        new_slot_id = request.POST.get('slot_id')
        try:
            with transaction.atomic():
                old_slot = TimeSlot.objects.select_for_update().get(
                    pk=booking.slot_id
                )
                new_slot = TimeSlot.objects.select_for_update().get(
                    pk=new_slot_id,
                    box__service=service,
                    status='free',
                )
                old_slot.status = 'free'
                old_slot.save(update_fields=['status'])
                new_slot.status = 'booked'
                new_slot.save(update_fields=['status'])
                booking.slot = new_slot
                booking.save(update_fields=['slot', 'updated_at'])
        except (IntegrityError, TimeSlot.DoesNotExist, ValueError):
            messages.error(request, 'Выбранное время уже недоступно.')
            return redirect('reschedule_booking', booking_id=booking.pk)
        messages.success(request, 'Запись перенесена.')
        send_telegram_notification(
            service,
            f'🔄 Клиент перенёс запись\nКлиент: {request.user.username}\n'
            f'Новое время: {new_slot.date} {new_slot.start_time:%H:%M}',
        )
        return redirect('my_bookings')

    return render(request, 'bookings/reschedule_booking.html', {
        'booking': booking,
        'available_slots': available_slots,
    })


@login_required
def owner_booking_status(request, booking_id, status):
    allowed_statuses = {'cancelled', 'no_show'}
    if status not in allowed_statuses:
        return redirect('home')
    booking = get_object_or_404(
        Booking,
        pk=booking_id,
        slot__box__service__owner=request.user,
        status__in=['confirmed', 'in_progress'],
    )
    if request.method == 'POST':
        booking.status = status
        booking.cancellation_reason = request.POST.get('reason', '').strip()
        booking.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
        booking.slot.status = 'free'
        booking.slot.save(update_fields=['status'])
        if booking.user:
            send_telegram_to_user(
                booking.user,
                f'❌ Запись в {booking.slot.box.service.name} отменена владельцем.',
            )
    return redirect(
        'owner_dashboard',
        service_id=booking.slot.box.service_id,
    )


@login_required
def owner_dashboard(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
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
        'owner_services': request.user.services.all(),
        'bookings': bookings,
        'total_bookings': total_bookings,
        'in_progress': in_progress,
        'free_slots': free_slots,
        'service_reviews': service.reviews.filter(is_approved=True).select_related('user')[:10],
    })


@login_required
def slot_in_progress(request, slot_id):
    slot = get_object_or_404(
        TimeSlot,
        pk=slot_id,
        box__service__owner=request.user,
    )
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    if request.method == 'POST':
        slot.status = 'in_progress'
        slot.save()
        # Уведомление клиенту
        booking = Booking.objects.filter(
            slot=slot,
            status__in=['confirmed', 'in_progress'],
        ).first()
        if booking:
            booking.status = 'in_progress'
            booking.save(update_fields=['status', 'updated_at'])
        if booking and booking.user:
            send_telegram_to_user(booking.user,
                f"🚀 Ваша запись началась!\n"
                f"Сервис: {slot.box.service.name}\n"
                f"{slot.box.name}\n"
                f"Время: {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"
            )
    return redirect('owner_dashboard', service_id=slot.box.service.pk)


@login_required
def slot_free(request, slot_id):
    slot = get_object_or_404(
        TimeSlot,
        pk=slot_id,
        box__service__owner=request.user,
    )
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')
    if request.method == 'POST':
        slot.status = 'free'
        slot.save()
        booking = Booking.objects.filter(
            slot=slot,
            status__in=['confirmed', 'in_progress'],
        ).first()
        if booking:
            booking.status = 'completed'
            booking.save(update_fields=['status', 'updated_at'])
    return redirect('owner_dashboard', service_id=slot.box.service.pk)


@login_required
def generate_slots(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')

    active_boxes = service.boxes.filter(is_active=True)
    if not active_boxes.exists():
        messages.error(request, f'❌ Сначала добавьте {service.category.slot_unit.lower()} — без них нельзя создать слоты!')
        return redirect('owner_dashboard', service_id=service.pk)

    if request.method == 'POST':
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        box_id = request.POST.get('box_id', 'all')

        if box_id == 'all':
            boxes = active_boxes
        else:
            boxes = active_boxes.filter(pk=box_id)

        try:
            interval = int(request.POST.get('interval', 60))
            start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            messages.error(request, 'Проверьте даты и длительность слота.')
            return redirect('generate_slots', service_id=service.pk)

        if interval < 15 or interval > 240:
            messages.error(request, 'Длительность слота должна быть от 15 до 240 минут.')
            return redirect('generate_slots', service_id=service.pk)
        if end_date < start_date:
            messages.error(request, 'Дата окончания не может быть раньше даты начала.')
            return redirect('generate_slots', service_id=service.pk)
        if (end_date - start_date).days > 366:
            messages.error(request, 'За один раз можно создать расписание максимум на год.')
            return redirect('generate_slots', service_id=service.pk)

        service_schedule = {
            row.weekday: row
            for row in service.weekly_schedules.filter(box__isnull=True)
        }
        box_schedules = {}
        for row in WeeklySchedule.objects.filter(
            service=service,
            box__in=boxes,
        ):
            box_schedules.setdefault(row.box_id, {})[row.weekday] = row

        breaks_by_weekday = {}
        for schedule_break in ScheduleBreak.objects.filter(service=service):
            breaks_by_weekday.setdefault(schedule_break.weekday, []).append(
                schedule_break
            )
        service_exceptions = {
            item.date: item
            for item in service.schedule_exceptions.filter(box__isnull=True)
        }
        box_exceptions = {}
        for item in ScheduleException.objects.filter(
            service=service,
            box__in=boxes,
            date__range=(start_date, end_date),
        ):
            box_exceptions.setdefault(item.box_id, {})[item.date] = item

        count = 0
        current_date = start_date
        while current_date <= end_date:
            for box in boxes:
                weekday = current_date.weekday()
                schedule = (
                    box_schedules.get(box.pk, {}).get(weekday)
                    or service_schedule.get(weekday)
                )
                exception = (
                    box_exceptions.get(box.pk, {}).get(current_date)
                    or service_exceptions.get(current_date)
                )
                if exception:
                    if exception.is_closed:
                        continue
                    opening_time = exception.start_time
                    closing_time = exception.end_time
                elif schedule:
                    if not schedule.is_working:
                        continue
                    opening_time = schedule.start_time
                    closing_time = schedule.end_time
                else:
                    opening_time = service.opening_time
                    closing_time = service.closing_time

                start = datetime.combine(current_date, opening_time)
                end = datetime.combine(current_date, closing_time)
                applicable_breaks = [
                    item for item in breaks_by_weekday.get(weekday, [])
                    if item.box_id is None or item.box_id == box.pk
                ]
                current = start
                while current + timedelta(minutes=interval) <= end:
                    slot_end = current + timedelta(minutes=interval)
                    overlaps_break = any(
                        current.time() < item.end_time
                        and slot_end.time() > item.start_time
                        for item in applicable_breaks
                    )
                    if overlaps_break:
                        current = slot_end
                        continue
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

    return render(request, 'bookings/generate_slots.html', {
        'service': service,
        'active_boxes': active_boxes,
    })


@login_required
def delete_slots(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')

    if request.method == 'POST':
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        time_from = request.POST.get('time_from')
        time_to = request.POST.get('time_to')

        slots = TimeSlot.objects.filter(box__service=service, status='free')

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
        status='completed',
    ).exists()

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if rating and comment and has_booking:
            Review.objects.update_or_create(
                user=request.user,
                service=service,
                defaults={'rating': rating, 'comment': comment}
            )
            messages.success(request, 'Отзыв оставлен!')
        elif not has_booking:
            messages.error(request, 'Отзыв можно оставить только после завершённой записи.')
        return redirect('service_detail', pk=service.pk)

    return render(request, 'bookings/add_review.html', {
        'service': service,
        'has_booking': has_booking,
    })


@login_required
def connect_telegram(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
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


@login_required
def analytics(request, service_id):
    service = get_object_or_404(Service, pk=service_id, owner=request.user)
    if request.user.role != 'business_owner':
        messages.error(request, 'Доступ запрещён.')
        return redirect('home')

    period = request.GET.get('period', '30')
    days = int(period)
    date_from = date_type.today() - timedelta(days=days)

    bookings = Booking.objects.filter(
        slot__box__service=service,
        slot__date__gte=date_from
    ).exclude(slot__status='free')

    total = bookings.count()

    bookings_by_day = {}
    for i in range(days):
        d = date_type.today() - timedelta(days=days-i-1)
        bookings_by_day[str(d)] = 0
    for b in bookings:
        key = str(b.slot.date)
        if key in bookings_by_day:
            bookings_by_day[key] += 1

    hours = {}
    for b in bookings:
        hour = b.slot.start_time.strftime('%H:00')
        hours[hour] = hours.get(hour, 0) + 1
    popular_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)[:5]

    top_clients = bookings.filter(user__isnull=False).values(
        'user__username', 'user__phone'
    ).annotate(count=Count('id')).order_by('-count')[:10]

    box_stats = bookings.values('slot__box__name').annotate(
        count=Count('id')
    ).order_by('-count')

    avg_rating = service.reviews.aggregate(Avg('rating'))['rating__avg']

    periods = [('7', '7 дней'), ('30', '30 дней'), ('90', '3 месяца'), ('365', '1 год')]

    return render(request, 'bookings/analytics.html', {
        'service': service,
        'period': period,
        'periods': periods,
        'total': total,
        'bookings_by_day': json.dumps(bookings_by_day),
        'popular_hours': popular_hours,
        'top_clients': top_clients,
        'box_stats': box_stats,
        'avg_rating': avg_rating,
    })


@login_required
def respond_review(request, review_id):
    review = get_object_or_404(
        Review,
        pk=review_id,
        service__owner=request.user,
    )
    if request.method == 'POST':
        review.owner_response = request.POST.get('owner_response', '').strip()
        review.save(update_fields=['owner_response'])
        messages.success(request, 'Ответ на отзыв сохранён.')
    return redirect('owner_dashboard', service_id=review.service_id)
