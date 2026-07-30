from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from cities.models import City
from services.models import (
    Box,
    ScheduleBreak,
    ScheduleException,
    Service,
    ServiceOffering,
    WeeklySchedule,
)

from .models import Booking, TimeSlot


class OwnerAccessTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='owner',
            password='password',
            role='business_owner',
        )
        self.other_owner = user_model.objects.create_user(
            username='other-owner',
            password='password',
            role='business_owner',
        )
        category = Category.objects.create(name='Test', slot_unit='Room')
        self.service = Service.objects.create(
            name='Private business',
            category=category,
            owner=self.owner,
            address='Test address',
            phone='123',
            latitude=0,
            longitude=0,
            opening_time=time(9),
            closing_time=time(18),
        )
        self.box = Box.objects.create(service=self.service, name='Room 1')
        self.slot = TimeSlot.objects.create(
            box=self.box,
            date=date.today(),
            start_time=time(10),
            end_time=time(11),
        )

    def test_owner_cannot_open_another_owners_dashboard(self):
        self.client.force_login(self.other_owner)

        response = self.client.get(
            reverse('owner_dashboard', args=[self.service.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_cannot_change_another_owners_slot(self):
        self.client.force_login(self.other_owner)

        response = self.client.post(
            reverse('slot_in_progress', args=[self.slot.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, 'free')

    def test_owner_cannot_add_resource_to_another_business(self):
        self.client.force_login(self.other_owner)

        response = self.client.post(
            reverse('add_box', args=[self.service.pk]),
            {'name': 'Unauthorized room'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            Box.objects.filter(name='Unauthorized room').exists()
        )

    def test_assigned_owner_can_open_dashboard(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('owner_dashboard', args=[self.service.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_slot_generation_respects_closed_days(self):
        WeeklySchedule.objects.create(
            service=self.service,
            weekday=0,
            is_working=False,
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('generate_slots', args=[self.service.pk]),
            {
                'date_from': '2026-08-03',
                'date_to': '2026-08-03',
                'interval': '60',
                'box_id': str(self.box.pk),
            },
        )

        self.assertRedirects(
            response,
            reverse('owner_dashboard', args=[self.service.pk]),
        )
        self.assertFalse(
            TimeSlot.objects.filter(date=date(2026, 8, 3)).exists()
        )

    def test_slot_generation_respects_breaks(self):
        WeeklySchedule.objects.create(
            service=self.service,
            weekday=0,
            is_working=True,
            start_time=time(9),
            end_time=time(13),
        )
        ScheduleBreak.objects.create(
            service=self.service,
            weekday=0,
            start_time=time(10),
            end_time=time(11),
            label='Lunch',
        )
        self.client.force_login(self.owner)

        self.client.post(
            reverse('generate_slots', args=[self.service.pk]),
            {
                'date_from': '2026-08-03',
                'date_to': '2026-08-03',
                'interval': '60',
                'box_id': str(self.box.pk),
            },
        )

        generated_starts = list(
            TimeSlot.objects.filter(date=date(2026, 8, 3))
            .values_list('start_time', flat=True)
        )
        self.assertEqual(
            generated_starts,
            [time(9), time(11), time(12)],
        )

    def test_resource_schedule_overrides_service_schedule(self):
        WeeklySchedule.objects.create(
            service=self.service,
            weekday=0,
            is_working=True,
            start_time=time(9),
            end_time=time(18),
        )
        WeeklySchedule.objects.create(
            service=self.service,
            box=self.box,
            weekday=0,
            is_working=True,
            start_time=time(12),
            end_time=time(14),
        )
        self.client.force_login(self.owner)

        self.client.post(
            reverse('generate_slots', args=[self.service.pk]),
            {
                'date_from': '2026-08-03',
                'date_to': '2026-08-03',
                'interval': '60',
                'box_id': str(self.box.pk),
            },
        )

        generated_starts = list(
            TimeSlot.objects.filter(date=date(2026, 8, 3))
            .values_list('start_time', flat=True)
        )
        self.assertEqual(generated_starts, [time(12), time(13)])

    def test_owner_cannot_manage_another_business_schedule(self):
        self.client.force_login(self.other_owner)

        response = self.client.get(
            reverse('manage_schedule', args=[self.service.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_assigned_owner_can_open_schedule_settings(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('manage_schedule', args=[self.service.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'График работы')

    def test_owner_can_toggle_resource_without_page_reload(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('toggle_box', args=[self.box.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['is_active'], False)
        self.box.refresh_from_db()
        self.assertFalse(self.box.is_active)

    def test_language_button_uses_selected_language(self):
        self.client.post(
            reverse('set_language'),
            {'language': 'en', 'next': '/'},
        )

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'class="active">🇬🇧 English</button>')

    def test_map_uses_selected_city_coordinates(self):
        city = City.objects.create(
            name='Aktau',
            name_ru='Актау',
            latitude=43.6532,
            longitude=51.1975,
        )
        session = self.client.session
        session['city_id'] = city.pk
        session['city_name'] = city.name_ru
        session.save()

        response = self.client.get(reverse('service_map'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_city'], city)
        self.assertJSONEqual(
            response.context['city_center_json'],
            [43.6532, 51.1975],
        )
        self.assertEqual(response.context['services_data'], [])

        self.service.city = city
        self.service.save(update_fields=['city'])
        filtered_response = self.client.get(
            reverse('service_map'),
            {'service': self.service.pk},
        )

        self.assertEqual(
            filtered_response.context['services_data'][0]['id'],
            self.service.pk,
        )

    def test_map_does_not_show_services_without_search(self):
        city = City.objects.create(
            name='Atyrau',
            name_ru='Атырау',
            latitude=47.1067,
            longitude=51.9214,
        )
        self.service.city = city
        self.service.save(update_fields=['city'])
        session = self.client.session
        session['city_id'] = city.pk
        session.save()

        response = self.client.get(reverse('service_map'))

        self.assertEqual(response.context['services_data'], [])
        self.assertFalse(response.context['has_filters'])

    def test_owner_can_create_offering(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('manage_catalog', args=[self.service.pk]),
            {
                'action': 'add_offering',
                'name': 'Diagnostics',
                'price': '5000',
                'duration_minutes': '45',
                'boxes': [self.box.pk],
            },
        )

        self.assertRedirects(
            response,
            reverse('manage_catalog', args=[self.service.pk]),
        )
        offering = ServiceOffering.objects.get(name='Diagnostics')
        self.assertEqual(offering.duration_minutes, 45)
        self.assertTrue(offering.boxes.filter(pk=self.box.pk).exists())

    def test_schedule_exception_prevents_slot_generation(self):
        ScheduleException.objects.create(
            service=self.service,
            date=date(2026, 8, 3),
            is_closed=True,
            label='Holiday',
        )
        self.client.force_login(self.owner)

        self.client.post(
            reverse('generate_slots', args=[self.service.pk]),
            {
                'date_from': '2026-08-03',
                'date_to': '2026-08-03',
                'interval': '60',
                'box_id': str(self.box.pk),
            },
        )

        self.assertFalse(
            TimeSlot.objects.filter(date=date(2026, 8, 3)).exists()
        )

    def test_cancelled_booking_keeps_history_and_releases_slot(self):
        client_user = get_user_model().objects.create_user(
            username='client',
            password='password',
        )
        self.slot.status = 'booked'
        self.slot.save(update_fields=['status'])
        booking = Booking.objects.create(user=client_user, slot=self.slot)
        self.client.force_login(client_user)

        self.client.post(reverse('cancel_booking', args=[booking.pk]))

        booking.refresh_from_db()
        self.slot.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')
        self.assertEqual(self.slot.status, 'free')
        replacement = Booking.objects.create(user=client_user, slot=self.slot)
        self.assertEqual(replacement.status, 'confirmed')
