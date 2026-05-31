import requests

from config import (
    TELEGRAM_SEND_MESSAGE_ENDPOINT,
    TELEGRAM_CHAT_ID
)


def send_message(text: str, reply_to_message_id: int = None):
    """Send a message to the Telegram chat, optionally replying to a specific message."""
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text
    }

    if reply_to_message_id:
        params['reply_to_message_id'] = reply_to_message_id

    try:
        response = requests.get(
            TELEGRAM_SEND_MESSAGE_ENDPOINT,
            params=params
        )
        return response.json()
    except Exception as e:
        print(f'Erro ao enviar mensagem no Telegram: {e}')
        return None
