import logging
import time
import os
import requests
import base64
from config import RESULT_FILES_PATH, EVOLUTION_API_URL, EVOLUTION_INSTANCE_NAME, EVOLUTION_GET_CHAT_ENDPOINT, EVOLUTION_GET_BASE64_MEDIA_ENDPOINT, EVOLUTION_API_KEY
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
        self.bot_ids = []
        self._init_bot_identity()

    def _init_bot_identity(self):
        from config import EVOLUTION_CONNECT_INSTANCE_ENDPOINT
        from app.messengers.whatsapp_client import WhatsAppClient
        
        client = WhatsAppClient()
        if not client.wait_until_ready():
            logger.warning("EvolutionAPI session did not become ready. Cannot fetch bot identity yet.")
            return False
            
        try:
            # Em Evolution v2, usamos fetchInstances para pegar ownerJid
            url = f"{EVOLUTION_API_URL}/instance/fetchInstances?instanceName={EVOLUTION_INSTANCE_NAME}"
            headers = {"apikey": EVOLUTION_API_KEY}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                owner_jid = None
                if isinstance(data, list) and len(data) > 0:
                    owner_jid = data[0].get('ownerJid')
                elif isinstance(data, dict):
                    owner_jid = data.get('instance', {}).get('ownerJid') or data.get('ownerJid')
                    
                if owner_jid and owner_jid not in self.bot_ids:
                    self.bot_ids.append(owner_jid)
                    
                    # Tentar obter o LID (necessário para menções no Evolution v2 Multi-Device)
                    from config import WHATSAPP_CHAT_ID, EVOLUTION_GET_CHAT_ENDPOINT
                    if WHATSAPP_CHAT_ID:
                        try:
                            group_url = f"{EVOLUTION_GET_CHAT_ENDPOINT}?groupJid={WHATSAPP_CHAT_ID}"
                            g_res = requests.get(group_url, headers=headers)
                            if g_res.status_code == 200:
                                participants = g_res.json().get('participants', [])
                                for p in participants:
                                    if p.get('phoneNumber') == owner_jid:
                                        lid = p.get('id')
                                        if lid and lid not in self.bot_ids:
                                            self.bot_ids.append(lid)
                        except Exception as e:
                            logger.error(f"Failed to fetch bot LID from group: {e}")

                logger.info(f"EvolutionAPI Bot Identity initialized: IDs={self.bot_ids}")
                return True
        except Exception as e:
            logger.error(f"Error fetching EvolutionAPI bot identity: {e}")
        return False

    def _get_chat_administrators(self, chat_id: str) -> list[str]:
        if not chat_id or not chat_id.endswith('@g.us'):
            return [chat_id]
            
        try:
            url = f"{EVOLUTION_GET_CHAT_ENDPOINT}?groupJid={chat_id}"
            headers = {"apikey": EVOLUTION_API_KEY}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            chat_data = response.json()
            
            admins = []
            participants = chat_data.get('participants', [])
            for p in participants:
                if p.get('admin') == 'admin' or p.get('admin') == 'superadmin':
                    admin_id = p.get('id')
                    if admin_id:
                        admins.append(admin_id)
            return admins
        except Exception as e:
            logger.error(f'Failed to get WhatsApp chat administrators: {e}')
            return []

    def _resolve_sender_id(self, from_id: str) -> str:
        # EvolutionAPI usually returns the correct s.whatsapp.net ID directly
        if not from_id or not from_id.endswith('@lid'):
            return from_id
        # Caso chegue algo lid (raro na Evolution API v2 para upserts normais)
        return from_id.replace('@lid', '@s.whatsapp.net')

    def _download_whatsapp_media(self, message):
        message_id = message.get('key', {}).get('id')
        date = message.get('messageTimestamp')
        
        # Evolution v2 indica media com messageType ou chaves dentro de message
        msg_obj = message.get('message', {})
        has_media = 'imageMessage' in msg_obj or message.get('messageType') == 'imageMessage'
        
        if not has_media:
            return
            
        logger.info(f"Downloading EvolutionAPI media for {message_id}")
        
        try:
            download_url = f"{EVOLUTION_GET_BASE64_MEDIA_ENDPOINT}"
            headers = {"apikey": EVOLUTION_API_KEY}
            payload = {
                "message": message
            }
            media_resp = requests.post(download_url, json=payload, headers=headers)
            media_resp.raise_for_status()
            media_data = media_resp.json()
            
            base64_data = media_data.get('base64')
            if not base64_data:
                logger.error("No base64 data returned by EvolutionAPI.")
                return
                
            # Evolution as vezes retorna "data:image/jpeg;base64,..."
            if "," in base64_data:
                base64_data = base64_data.split(',')[1]

            file_name = f"wa_{message_id}.jpg"
            
            os.makedirs(RESULT_FILES_PATH, exist_ok=True)
            file_path = os.path.join(RESULT_FILES_PATH, file_name)
            with open(file_path, "wb") as file:
                file.write(base64.b64decode(base64_data))
                
            save_media_metadata(file_name, str(message_id), date)
            
        except Exception as e:
            logger.error(f"Failed to download EvolutionAPI media: {e}")
            try:
                from app.messengers import get_messenger
                from app.messages.system import ERROR_UNEXPECTED_MESSAGES
                import random
                messenger = get_messenger()
                messenger.send_message(random.choice(ERROR_UNEXPECTED_MESSAGES), reply_to_message_id=str(message_id), msg_type="ERROR")
            except:
                pass

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
            
        logger.info(f"Processing EvolutionAPI batch of {len(batch)} messages.")
        
        if not self.bot_ids:
            self._init_bot_identity()
        
        has_photo = False
        processing_msg_sent = False
        for message in batch:
            msg_obj = message.get('message', {})
            
            text = ""
            if 'conversation' in msg_obj:
                text = msg_obj['conversation']
            elif 'extendedTextMessage' in msg_obj:
                text = msg_obj['extendedTextMessage'].get('text', '')
            elif 'imageMessage' in msg_obj:
                text = msg_obj['imageMessage'].get('caption', '')

            message_id = message.get('key', {}).get('id')
            chat_id = message.get('key', {}).get('remoteJid')
            
            # participant holds the actual sender ID in groups
            from_id = message.get('key', {}).get('participant') or chat_id
            
            if text.startswith('/'):
                admins = self._get_chat_administrators(chat_id)
                from_id = self._resolve_sender_id(from_id)
                
                is_admin = from_id in admins
                handle_command(text, str(message_id), from_id, chat_id, is_admin=is_admin)
                continue

            msg_to = chat_id # in groups remoteJid is the group, in private it's the sender
            
            is_mentioned = False
            extended_msg = msg_obj.get('extendedTextMessage', {})
            mentioned_ids = extended_msg.get('contextInfo', {}).get('mentionedJid', [])
            if not mentioned_ids:
                mentioned_ids = message.get('contextInfo', {}).get('mentionedJid', [])
            
            if any(b_id in mentioned_ids for b_id in self.bot_ids) or (msg_to in mentioned_ids and msg_to.endswith('@s.whatsapp.net')):
                is_mentioned = True
                
            if is_mentioned and text.strip():
                import re
                for b_id in self.bot_ids:
                    bot_num = b_id.split('@')[0]
                    text = re.sub(f"(?i)@{bot_num}", "", text).strip()
                
                logger.info(f"EvolutionAPI Bot mentioned! Attempting AI routing for text: {text}")
                
                if len(text) > 300:
                    from app.messages.ai import AI_TOO_LONG_MESSAGES
                    import random
                    from app.messengers import get_messenger
                    messenger = get_messenger()
                    messenger.send_message(random.choice(AI_TOO_LONG_MESSAGES), reply_to_message_id=str(message_id), msg_type="AI_TOO_LONG")
                    continue
                    
                from app.ai_router import route_message_to_command
                from app.messages.ai import AI_ERROR_MESSAGES, AI_INVALID_MAPPING_MESSAGES
                import random
                from app.messengers import get_messenger
                
                cmd_or_err = route_message_to_command(text)
                messenger = get_messenger()
                
                if cmd_or_err == "ERROR_API":
                    messenger.send_message(random.choice(AI_ERROR_MESSAGES), reply_to_message_id=str(message_id), msg_type="AI_ERROR")
                elif cmd_or_err == "ERROR_MAPPING":
                    messenger.send_message(random.choice(AI_INVALID_MAPPING_MESSAGES), reply_to_message_id=str(message_id), msg_type="AI_MAPPING_ERROR")
                elif cmd_or_err:
                    admins = self._get_chat_administrators(chat_id)
                    from_id = self._resolve_sender_id(from_id)
                    is_admin = from_id in admins
                    logger.info(f"AI Routed command: {cmd_or_err}")
                    handle_command(cmd_or_err, str(message_id), from_id, chat_id, is_admin=is_admin)
                continue

            has_media = 'imageMessage' in msg_obj or message.get('messageType') == 'imageMessage'
            if has_media:
                has_photo = True
                self._download_whatsapp_media(message)
                self.last_processed_id = message_id
                
                if not processing_msg_sent:
                    try:
                        from app.messages.system import PROCESSING_MESSAGES
                        import random
                        from app.messengers import get_messenger
                        messenger = get_messenger()
                        messenger.send_message(
                            random.choice(PROCESSING_MESSAGES),
                            reply_to_message_id=str(message_id),
                            msg_type="SYSTEM_PROCESSING"
                        )
                        processing_msg_sent = True
                    except Exception as e:
                        logger.error(f"Failed to send processing message: {e}")

        if has_photo:
            logger.info("Finished downloading EvolutionAPI media from batch.")
            return self.last_processed_id
            
        return None

    def confirm_updates(self, last_update_id: int):
        pass
