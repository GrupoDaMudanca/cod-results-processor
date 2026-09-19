import requests
import logging
import base64
import os

logger = logging.getLogger(__name__)

from app.messengers.base import MessengerClient
from config import EVOLUTION_SEND_TEXT_ENDPOINT, EVOLUTION_SEND_MEDIA_ENDPOINT, EVOLUTION_API_KEY, WHATSAPP_CHAT_ID

class WhatsAppClient(MessengerClient):
    def send_message(self, text: str, reply_to_message_id: str = None, msg_type: str = "UNKNOWN", chat_id: str = None):
        target_chat = chat_id or WHATSAPP_CHAT_ID
        if not target_chat:
            logger.error("WHATSAPP_CHAT_ID is not configured in environment variables.")
            return None
            
        payload = {
            "number": target_chat,
            "text": text
        }
        
        if reply_to_message_id:
            payload["quoted"] = {
                "key": {
                    "id": reply_to_message_id
                }
            }
        
        headers = {
            "apikey": EVOLUTION_API_KEY
        }

        try:
            logger.info(f"[EVOLUTION_OUTGOING] Type: {msg_type} | Message: {text}")
            response = requests.post(EVOLUTION_SEND_TEXT_ENDPOINT, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Failed to send Evolution message: {e} - Response: {e.response.text}")
            else:
                logger.error(f"Failed to send Evolution message: {e}")
            return None

    def send_photo(self, photo_path: str, caption: str = None, reply_to_message_id: str = None, msg_type: str = "UNKNOWN", chat_id: str = None):
        target_chat = chat_id or WHATSAPP_CHAT_ID
        if not target_chat:
            logger.error("WHATSAPP_CHAT_ID is not configured in environment variables.")
            return None
            
        try:
            with open(photo_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            mimetype = "image/png" if photo_path.endswith('.png') else "image/jpeg"
            
            payload = {
                "number": target_chat,
                "mediatype": "image",
                "mimetype": mimetype,
                "caption": caption or "",
                "media": encoded_string
            }
            
            if reply_to_message_id:
                payload["quoted"] = {
                    "key": {
                        "id": reply_to_message_id
                    }
                }
            
            headers = {
                "apikey": EVOLUTION_API_KEY
            }

            logger.info(f"[EVOLUTION_OUTGOING] Type: {msg_type} | Photo with caption: {caption}")
            response = requests.post(EVOLUTION_SEND_MEDIA_ENDPOINT, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Failed to send Evolution photo: {e} - Response: {e.response.text}")
            else:
                logger.error(f"Failed to send Evolution photo: {e}")
            return None

    def wait_until_ready(self) -> bool:
        if not WHATSAPP_CHAT_ID:
            return False
            
        import time
        from config import EVOLUTION_CONNECT_INSTANCE_ENDPOINT, EVOLUTION_API_KEY
        
        headers = {
            "apikey": EVOLUTION_API_KEY
        }
        
        logger.info("Checking if EvolutionAPI session is ready...")
        max_retries = 36 # 3 minutes total
        for _ in range(max_retries):
            try:
                response = requests.get(EVOLUTION_CONNECT_INSTANCE_ENDPOINT, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # Example Evolution v2 connect response contains state
                    instance_data = data.get('instance', {})
                    if instance_data.get('state') == 'open' or data.get('state') == 'open':
                        logger.info("EvolutionAPI session is connected.")
                        return True
            except Exception:
                pass
            
            logger.info("EvolutionAPI session not ready yet. Retrying in 5 seconds...")
            time.sleep(5)
            
        logger.warning("EvolutionAPI session did not become ready within the timeout.")
        return False
