from config import MESSENGER_PROVIDER
from app.messengers.telegram_client import TelegramClient
from app.messengers.whatsapp_client import WhatsAppClient

def get_messenger():
    if MESSENGER_PROVIDER == 'whatsapp':
        return WhatsAppClient()
    return TelegramClient()
