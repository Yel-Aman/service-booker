from django.db import migrations


def backfill_booking_status(apps, schema_editor):
    Booking = apps.get_model('bookings', 'Booking')
    Booking.objects.filter(slot__status='free', status='confirmed').update(
        status='completed',
    )
    Booking.objects.filter(slot__status='in_progress', status='confirmed').update(
        status='in_progress',
    )


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0007_booking_reminder_sent_at'),
    ]

    operations = [
        migrations.RunPython(
            backfill_booking_status,
            migrations.RunPython.noop,
        ),
    ]
