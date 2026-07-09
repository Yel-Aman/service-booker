import os
import requests
from services.models import Service

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')


def process_updates():
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
    response = requests.get(url).json()

    for update in response.get('result', []):
        message = update.get('message', {})
        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id')

        if not text or not chat_id:
            continue

        # Владелец подключает сервис
        if text.startswith('/connect '):
            try:
                service_id = int(text.replace('/connect ', '').strip())
                service = Service.objects.get(pk=service_id)
                service.telegram_chat_id = str(chat_id)
                service.save()
                send_message(chat_id, f'✅ Telegram подключён к сервису "{service.name}"! Теперь вы будете получать уведомления о новых бронях здесь.')
            except (ValueError, Service.DoesNotExist):
                send_message(chat_id, '❌ Неверный код подключения.')

        # Клиент подключает свой аккаунт
        elif text.startswith('/client '):
            try:
                from users.models import CustomUser
                username = text.replace('/client ', '').strip()
                user = CustomUser.objects.get(username=username)
                user.telegram_chat_id = str(chat_id)
                user.save()
                send_message(chat_id, f'✅ Telegram подключён к аккаунту {username}! Теперь вы будете получать уведомления о своих бронях.')
            except Exception:
                send_message(chat_id, '❌ Пользователь не найден.')


def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    requests.post(url, data={'chat_id': chat_id, 'text': text})