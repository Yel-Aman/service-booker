from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Booking
from bookings.views import send_telegram_to_user


class Command(BaseCommand):
    help = 'Отправляет Telegram-напоминания о записях в ближайшие три часа.'

    def handle(self, *args, **options):
        now = timezone.localtime()
        until = now + timedelta(hours=3)
        bookings = Booking.objects.filter(
            status='confirmed',
            user__isnull=False,
            user__telegram_chat_id__gt='',
            reminder_sent_at__isnull=True,
            slot__date__range=(now.date(), until.date()),
        ).select_related('user', 'slot__box__service')

        sent = 0
        for booking in bookings:
            starts_at = timezone.make_aware(
                datetime.combine(
                    booking.slot.date,
                    booking.slot.start_time,
                ),
                timezone.get_current_timezone(),
            )
            if now <= starts_at <= until:
                send_telegram_to_user(
                    booking.user,
                    f'⏰ Напоминание о записи\n'
                    f'Сервис: {booking.slot.box.service.name}\n'
                    f'Дата: {booking.slot.date}\n'
                    f'Время: {booking.slot.start_time:%H:%M}\n'
                    f'Адрес: {booking.slot.box.service.address}',
                )
                booking.reminder_sent_at = timezone.now()
                booking.save(update_fields=['reminder_sent_at'])
                sent += 1

        self.stdout.write(self.style.SUCCESS(f'Отправлено напоминаний: {sent}'))
