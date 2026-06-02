import requests
import logging
import base64
import os

logger = logging.getLogger(__name__)

from app.messengers.base import MessengerClient
from config import WHATSAPP_SEND_MESSAGE_ENDPOINT, WHATSAPP_CHAT_ID

class WhatsAppClient(MessengerClient):
    def send_message(self, text: str, reply_to_message_id: str = None, msg_type: str = "UNKNOWN"):
        if not WHATSAPP_CHAT_ID:
            logger.error("WHATSAPP_CHAT_ID is not configured in environment variables.")
            return None
            
        payload = {
            "chatId": WHATSAPP_CHAT_ID,
            "contentType": "string",
            "content": text
        }
        if reply_to_message_id:
            payload["options"] = {"quotedMessageId": reply_to_message_id}

        try:
            logger.info(f"[WHATSAPP_OUTGOING] Type: {msg_type} | Message: {text}")
            response = requests.post(WHATSAPP_SEND_MESSAGE_ENDPOINT, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Failed to send WhatsApp message: {e} - Response: {e.response.text}")
            else:
                logger.error(f"Failed to send WhatsApp message: {e}")
            return None

    def send_photo(self, photo_path: str, caption: str = None, reply_to_message_id: str = None, msg_type: str = "UNKNOWN"):
        if not WHATSAPP_CHAT_ID:
            logger.error("WHATSAPP_CHAT_ID is not configured in environment variables.")
            return None
            
        try:
            with open(photo_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            # wwebjs-api handles MessageMedia.fromFilePath or base64. We will use the MessageMedia structure if it supports it, 
            # but usually the endpoint accepts base64 content type or url.
            # Looking at wwebjs-api docs: "contentType": "MessageMedia", "content": { "mimetype": "image/jpeg", "data": "base64..." }
            # Wait, let's just use string to send base64 if there's a specific endpoint. 
            # Usually /client/sendMessage accepts content as a base64 string if contentType is 'MessageMedia'
            
            # Fallback: using MessageMedia
            mimetype = "image/png" if photo_path.endswith('.png') else "image/jpeg"
            
            payload = {
                "chatId": WHATSAPP_CHAT_ID,
                "contentType": "MessageMedia",
                "content": {
                    "mimetype": mimetype,
                    "data": encoded_string,
                    "filename": os.path.basename(photo_path)
                }
            }
            options = {}
            if caption:
                options["caption"] = caption
            if reply_to_message_id:
                options["quotedMessageId"] = reply_to_message_id
            
            if options:
                payload["options"] = options

            logger.info(f"[WHATSAPP_OUTGOING] Type: {msg_type} | Photo with caption: {caption}")
            response = requests.post(WHATSAPP_SEND_MESSAGE_ENDPOINT, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Failed to send WhatsApp photo: {e} - Response: {e.response.text}")
            else:
                logger.error(f"Failed to send WhatsApp photo: {e}")
            return None
