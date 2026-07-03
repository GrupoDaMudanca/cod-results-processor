import logging
import os
import requests
from config import (
    TELEGRAM_GET_UPDATES_ENDPOINT,
    TELEGRAM_GET_FILE_ENDPOINT,
    TELEGRAM_DOWNLOAD_FILE_ENDPOINT,
    TELEGRAM_CHAT_ID,
    RESULT_FILES_PATH
)
from app.command_handler import handle_command
from app.media_handler import save_media_metadata
from app.listeners.base import BaseListener

logger = logging.getLogger(__name__)

class TelegramListener(BaseListener):
    def __init__(self):
        super().__init__()
        self.bot_id = None
        self.bot_username = None
        self._init_bot_identity()

    def _init_bot_identity(self):
        from config import TELEGRAM_GET_ME_ENDPOINT
        try:
            response = requests.get(TELEGRAM_GET_ME_ENDPOINT, timeout=10).json()
            if response.get('ok'):
                self.bot_id = str(response.get('result', {}).get('id'))
                self.bot_username = response.get('result', {}).get('username')
                logger.info(f"Telegram Bot Identity: ID={self.bot_id}, Username={self.bot_username}")
            else:
                logger.error(f"Failed to get bot identity: {response}")
        except Exception as e:
            logger.error(f"Error getting bot identity: {e}")

    def _get_chat_administrators(self) -> list[str]:
        """Get a list of administrator user IDs for the chat."""
        from config import TELEGRAM_GET_CHAT_ADMINISTRATORS_ENDPOINT
        params = {'chat_id': TELEGRAM_CHAT_ID}
        try:
            response = requests.get(TELEGRAM_GET_CHAT_ADMINISTRATORS_ENDPOINT, params=params, timeout=10).json()
            if response.get('ok'):
                return [str(admin.get('user', {}).get('id')) for admin in response.get('result', [])]
            logger.error(f"Failed to get chat administrators: {response.get('description')}")
            return []
        except Exception as e:
            logger.error(f'Failed to get chat administrators: {e}')
            return []

    def _is_message_photo(self, message) -> bool:
        return 'photo' in set(message.keys()) - {'message_id', 'from', 'chat', 'date'}

    def _get_updates(self, offset: int = None, chat_id: int = None, confirm_only: bool = False, timeout: int = 30):
        if confirm_only and not offset:
            raise Exception('You must provide an offset to confirm')
        elif offset:
            offset += 1

        params = {'offset': offset}
        if not confirm_only:
            params['timeout'] = timeout

        updates = requests.get(
            TELEGRAM_GET_UPDATES_ENDPOINT,
            params=params,
            timeout=timeout + 5 if not confirm_only else 10
        ).json()

        if not updates.get('ok', False) and not confirm_only:
            raise Exception(f"Failed to get updates! Response: {updates}")

        if updates.get('result'):
            logger.info(f"Raw updates from Telegram: {updates.get('result')}")
        elif not updates.get('ok', False) and confirm_only:
            return False
        elif updates.get('ok', False) and confirm_only:
            return True

        return [
            update for update in updates.get('result')
            if (not chat_id or update.get('message', {}).get('chat', {}).get('id') == chat_id)
            and update.get('message')
        ]

    def _download_file(self, file_id: str, message_id: int = None, date: int = None):
        file_path = requests.get(
            TELEGRAM_GET_FILE_ENDPOINT,
            params={'file_id': file_id}
        ).json().get('result').get('file_path')

        logger.info(f'Got {file_id}: {file_path}')

        file_name = file_path.split('/')[-1]
        file_endpoint = f'{TELEGRAM_DOWNLOAD_FILE_ENDPOINT}/{file_path}'

        os.makedirs(RESULT_FILES_PATH, exist_ok=True)
        with open(os.path.join(RESULT_FILES_PATH, file_name), "wb") as file:
            file.write(requests.get(file_endpoint).content)

        save_media_metadata(file_name, str(message_id), date)

    def poll_and_download(self, timeout: int = 30) -> int:
        updates = self._get_updates(chat_id=int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else None, timeout=timeout)

        if not updates:
            return None

        logger.info(f"Processing batch of {len(updates)} updates.")

        has_photo = False
        processing_msg_sent = False
        for update in updates:
            message = update.get('message')
            if not message:
                continue
                
            text = message.get('text', '')
            message_id = message.get('message_id')
            from_id = str(message.get('from', {}).get('id', ''))
            chat_id = str(message.get('chat', {}).get('id', ''))
            
            if text.startswith('/'):
                admins = self._get_chat_administrators()
                is_admin = from_id in admins
                handle_command(text, str(message_id), from_id, chat_id, is_admin)
                continue
                
            # Check for native mention or private chat
            is_mentioned = False
            entities = message.get('entities', [])
            for ent in entities:
                if ent.get('type') == 'mention':
                    offset = ent.get('offset', 0)
                    length = ent.get('length', 0)
                    mention_text = text[offset:offset+length]
                    if self.bot_username and mention_text.lower() == f"@{self.bot_username.lower()}":
                        is_mentioned = True
                        break
                        
            chat_type = message.get('chat', {}).get('type')
            reply_to_user_id = str(message.get('reply_to_message', {}).get('from', {}).get('id', ''))
            
            if chat_type == 'private' or reply_to_user_id == self.bot_id:
                is_mentioned = True
                
            if is_mentioned and text.strip():
                # Clean up mentions to save tokens
                import re
                if self.bot_username:
                    text = re.sub(f"(?i)@{self.bot_username}", "", text).strip()
                
                logger.info(f"Bot mentioned! Attempting AI routing for text: {text}")
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
                    admins = self._get_chat_administrators()
                    is_admin = from_id in admins
                    logger.info(f"AI Routed command: {cmd_or_err}")
                    handle_command(cmd_or_err, str(message_id), from_id, chat_id, is_admin)
                continue
                
            if self._is_message_photo(message):
                has_photo = True
                logger.info("Found photo in message! Downloading...")
                
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
                    
                file_id = message.get('photo')[-1].get('file_id')
                date = message.get('date')
                self._download_file(file_id, message_id, date)

        if has_photo:
            logger.info("Finished downloading photos from updates batch.")

        last_update_id = updates[-1].get('update_id')
        return last_update_id

    def confirm_updates(self, last_update_id: int):
        self._get_updates(offset=last_update_id, confirm_only=True)

