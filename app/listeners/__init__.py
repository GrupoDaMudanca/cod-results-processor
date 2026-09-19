from app.listeners.whatsapp_listener import WhatsAppListener

_listener_instance = None

def get_listener():
    global _listener_instance
    if not _listener_instance:
        _listener_instance = WhatsAppListener()
    return _listener_instance
