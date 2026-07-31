from django.test import TestCase
from django.urls import reverse


class HomeTranslationTests(TestCase):
    def test_home_how_it_works_text_is_translated_to_kazakh(self):
        self.client.post(
            reverse('set_language'),
            {'language': 'kk', 'next': reverse('home')},
        )

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Қызметті табыңыз')
        self.assertContains(response, 'Санатты таңдап, қолайлы орынды табыңыз')

    def test_home_how_it_works_text_is_translated_to_english(self):
        self.client.post(
            reverse('set_language'),
            {'language': 'en', 'next': reverse('home')},
        )

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Find a service')
        self.assertContains(response, 'Choose a category and find the right place')
