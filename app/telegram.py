import requests
import logging

logger = logging.getLogger(__name__)

from config import (
    TELEGRAM_SEND_MESSAGE_ENDPOINT,
    TELEGRAM_SEND_PHOTO_ENDPOINT,
    TELEGRAM_GET_CHAT_ADMINISTRATORS_ENDPOINT,
    TELEGRAM_CHAT_ID
)


def send_message(text: str, reply_to_message_id: int = None, msg_type: str = "UNKNOWN"):
    """Send a message to the Telegram chat, optionally replying to a specific message."""
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text
    }

    if reply_to_message_id:
        params['reply_to_message_id'] = reply_to_message_id

    try:
        logger.info(f"[TELEGRAM_OUTGOING] Type: {msg_type} | Message: {text}")
        response = requests.get(
            TELEGRAM_SEND_MESSAGE_ENDPOINT,
            params=params
        )
        return response.json()
    except Exception as e:
        logger.error(f'Failed to send Telegram message: {e}')
        return None


def send_photo(photo_path: str, caption: str = None, reply_to_message_id: int = None, msg_type: str = "UNKNOWN"):
    """Send a photo to the Telegram chat."""
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': TELEGRAM_CHAT_ID}
            if caption:
                data['caption'] = caption
            if reply_to_message_id:
                data['reply_to_message_id'] = reply_to_message_id
            
            logger.info(f"[TELEGRAM_OUTGOING] Type: {msg_type} | Photo with caption: {caption}")
            response = requests.post(
                TELEGRAM_SEND_PHOTO_ENDPOINT,
                data=data,
                files=files
            )
            resp_json = response.json()
            if not resp_json.get('ok'):
                logger.error(f"Telegram API Error in send_photo: {resp_json}")
            return resp_json
    except Exception as e:
        logger.error(f'Failed to send Telegram photo: {e}')
        return None

def get_chat_administrators() -> list[str]:
    """Get a list of administrator user IDs for the chat."""
    params = {
        'chat_id': TELEGRAM_CHAT_ID
    }
    try:
        response = requests.get(
            TELEGRAM_GET_CHAT_ADMINISTRATORS_ENDPOINT,
            params=params
        ).json()
        if response.get('ok'):
            # Return list of user IDs (as strings for easier comparison)
            return [str(admin.get('user', {}).get('id')) for admin in response.get('result', [])]
        logger.error(f"Failed to get chat administrators: {response.get('description')}")
        return []
    except Exception as e:
        logger.error(f'Failed to get chat administrators: {e}')
        return []
