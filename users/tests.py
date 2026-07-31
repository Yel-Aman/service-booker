from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import UserDailyActivity


class PlatformDashboardTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username='platform-owner',
            password='password',
            email='owner@example.com',
        )
        self.client_user = get_user_model().objects.create_user(
            username='ordinary-client',
            password='password',
        )

    def test_only_superuser_can_open_platform_dashboard(self):
        self.client.force_login(self.client_user)
        denied = self.client.get(reverse('platform_dashboard'))
        self.assertEqual(denied.status_code, 302)

        self.client.force_login(self.superuser)
        response = self.client.get(reverse('platform_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Состояние платформы')

    def test_authenticated_visit_is_counted_once_per_day(self):
        self.client.force_login(self.client_user)

        self.client.get(reverse('home'))
        self.client.get(reverse('service_list'))

        self.assertEqual(
            UserDailyActivity.objects.filter(
                user=self.client_user,
                date=timezone.localdate(),
            ).count(),
            1,
        )

    def test_dashboard_shows_daily_active_users(self):
        UserDailyActivity.objects.create(
            user=self.client_user,
            date=timezone.localdate(),
        )
        self.client.force_login(self.superuser)

        response = self.client.get(reverse('platform_dashboard'))

        self.assertGreaterEqual(response.context['dau'], 1)


class LoginRedirectTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='booking-client',
            password='password',
        )

    def test_login_returns_user_to_requested_page(self):
        destination = reverse('profile')

        login_page = self.client.get(reverse('login'), {'next': destination})
        self.assertContains(login_page, f'name="next" value="{destination}"')

        response = self.client.post(reverse('login'), {
            'username': self.user.username,
            'password': 'password',
            'next': destination,
        })

        self.assertRedirects(response, destination)

    def test_login_does_not_redirect_to_external_site(self):
        response = self.client.post(reverse('login'), {
            'username': self.user.username,
            'password': 'password',
            'next': 'https://example.com/unsafe/',
        })

        self.assertRedirects(response, reverse('home'))
