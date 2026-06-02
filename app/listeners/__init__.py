from config import MESSENGER_PROVIDER
from app.listeners.telegram_listener import TelegramListener
from app.listeners.whatsapp_listener import WhatsAppListener

_listener_instance = None

def get_listener():
    global _listener_instance
    if not _listener_instance:
        if MESSENGER_PROVIDER == 'whatsapp':
            _listener_instance = WhatsAppListener()
        else:
            _listener_instance = TelegramListener()
    return _listener_instance
