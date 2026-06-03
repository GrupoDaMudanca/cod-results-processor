import logging
import time
import os
import requests
import base64
from config import RESULT_FILES_PATH, WHATSAPP_API_URL, WHATSAPP_SESSION_ID, WHATSAPP_GET_MESSAGE_ENDPOINT, WHATSAPP_DOWNLOAD_MEDIA_ENDPOINT, WHATSAPP_GET_CHAT_ENDPOINT
from app.command_handler import handle_command
from app.media_handler import save_media_metadata
from app.listeners.base import BaseListener
from app.listeners.whatsapp_webhook import WhatsAppWebhookServer

logger = logging.getLogger(__name__)

class WhatsAppListener(BaseListener):
    def __init__(self):
        self.whatsapp_queue = []
        self.last_processed_id = 0
        self.webhook_server = WhatsAppWebhookServer(self.whatsapp_queue)
        self.webhook_server.start_in_background()

    def _get_chat_administrators(self, chat_id: str) -> list[str]:
        """Get a list of administrator user IDs for the WhatsApp group."""
        if not chat_id or not chat_id.endswith('@g.us'):
            return [chat_id] # If it's a private chat, the user is their own admin
            
        try:
            response = requests.post(WHATSAPP_GET_CHAT_ENDPOINT, json={"chatId": chat_id})
            response.raise_for_status()
            chat_data = response.json()
            
            admins = []
            chat_obj = chat_data.get('chat', {})
            participants = chat_obj.get('groupMetadata', {}).get('participants', []) if chat_obj.get('isGroup') else []
            for p in participants:
                if p.get('isAdmin') or p.get('isSuperAdmin'):
                    admin_id = p.get('id', {}).get('_serialized')
                    if admin_id:
                        admins.append(admin_id)
            return admins
        except Exception as e:
            logger.error(f'Failed to get WhatsApp chat administrators: {e}')
            return []

    def _download_whatsapp_media(self, message):
        message_id_obj = message.get('id', {})
        message_id = message_id_obj.get('id')
        date = message.get('timestamp')
        
        has_media = message.get('hasMedia', False)
        if not has_media:
            return
            
        logger.info(f"Downloading WhatsApp media for {message_id}")
        
        try:
            # For downloading media, the API expects the short ID, not the _serialized ID
            short_id = message_id_obj.get('id')
            chat_id = message.get('from')
            
            download_url = f"{WHATSAPP_DOWNLOAD_MEDIA_ENDPOINT}"
            payload = {
                "chatId": chat_id,
                "messageId": short_id
            }
            media_resp = requests.post(download_url, json=payload)
            media_resp.raise_for_status()
            media_data = media_resp.json()
            
            if not media_data.get('success') or 'messageMedia' not in media_data:
                logger.error("No media data returned.")
                return
                
            msg_media = media_data['messageMedia']
            base64_data = msg_media['data']
            # Save as .jpg so it's picked up by match_processor
            file_name = f"wa_{message_id}.jpg"
            
            os.makedirs(RESULT_FILES_PATH, exist_ok=True)
            file_path = os.path.join(RESULT_FILES_PATH, file_name)
            with open(file_path, "wb") as file:
                file.write(base64.b64decode(base64_data))
                
            save_media_metadata(file_name, str(message_id), date)
            
        except Exception as e:
            logger.error(f"Failed to download WhatsApp media: {e}")

    def poll_and_download(self, timeout: int = 30) -> int:
        elapsed = 0
        while not self.whatsapp_queue and elapsed < timeout:
            time.sleep(1)
            elapsed += 1

        if not self.whatsapp_queue:
            return None

        time.sleep(2)
        
        batch = []
        while self.whatsapp_queue:
            batch.append(self.whatsapp_queue.pop(0))
            
        logger.info(f"Processing WhatsApp batch of {len(batch)} messages.")
        
        has_photo = False
        processing_msg_sent = False
        for message in batch:
            text = message.get('body', '')
            message_id_obj = message.get('id', {})
            message_id = message_id_obj.get('_serialized') or message_id_obj.get('id')
            from_id = message.get('author') or message.get('from')
            chat_id = message.get('from')
            
            if text.startswith('/'):
                admins = self._get_chat_administrators(chat_id)
                from_id = message.get('author') or message.get('from')
                
                # If from_id is a .lid, resolve it to the .c.us ID using the wwebjs-api contact endpoint
                if from_id and from_id.endswith('@lid'):
                    try:
                        url = f"{WHATSAPP_API_URL}/contact/getClassInfo/{WHATSAPP_SESSION_ID}"
                        contact_resp = requests.post(url, json={"contactId": from_id})
                        if contact_resp.status_code == 200:
                            contact_data = contact_resp.json()
                            if contact_data.get('success'):
                                real_id = contact_data.get('contact', {}).get('id', {}).get('_serialized')
                                if real_id:
                                    from_id = real_id
                    except Exception as e:
                        logger.error(f"Failed to resolve .lid contact: {e}")
                
                is_admin = from_id in admins
                handle_command(text, str(message_id), from_id, chat_id, is_admin=is_admin)
                continue
                
            if message.get('hasMedia', False) and message.get('type') == 'image':
                has_photo = True
                
                if not processing_msg_sent:
                    try:
                        from app.messengers import get_messenger
                        from app.messages import PROCESSING_MESSAGES
                        import random
                        messenger = get_messenger()
                        messenger.send_message(
                            random.choice(PROCESSING_MESSAGES),
                            msg_type="PROCESSING"
                        )
                        processing_msg_sent = True
                    except Exception as e:
                        logger.error(f"Failed to send processing message: {e}")
                        
                self._download_whatsapp_media(message)
                
        if has_photo:
            logger.info("Finished downloading WhatsApp media from batch.")
            
        self.last_processed_id += 1
        return self.last_processed_id

    def confirm_updates(self, last_update_id: int):
        pass

