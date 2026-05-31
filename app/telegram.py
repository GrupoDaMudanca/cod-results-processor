import requests
import logging

logger = logging.getLogger(__name__)

from config import (
    TELEGRAM_SEND_MESSAGE_ENDPOINT,
    TELEGRAM_SEND_PHOTO_ENDPOINT,
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
        logger.error(f'Failed to send Telegram message: {e}')
        return None


def send_photo(photo_path: str, caption: str = None, reply_to_message_id: int = None):
    """Send a photo to the Telegram chat."""
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': TELEGRAM_CHAT_ID}
            if caption:
                data['caption'] = caption
            if reply_to_message_id:
                data['reply_to_message_id'] = reply_to_message_id
            response = requests.post(
                TELEGRAM_SEND_PHOTO_ENDPOINT,
                data=data,
                files=files
            )
            return response.json()
    except Exception as e:
        logger.error(f'Failed to send Telegram photo: {e}')
        return None
