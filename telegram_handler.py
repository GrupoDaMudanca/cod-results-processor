
import json
import random
import requests
import logging
import re
import os

logger = logging.getLogger(__name__)

from app.telegram import send_message, get_chat_administrators, send_photo
from app.messages import (
    PROCESSING_MESSAGES, BACKFILL_START_MESSAGES, BACKFILL_END_MESSAGES,
    UNAUTHORIZED_MESSAGES, INVALID_BACKFILL_FORMAT_MESSAGES,
    DASHBOARD_START_MESSAGES, DASHBOARD_END_MESSAGES,
    DASHBOARD_NO_DATA_MESSAGES, DASHBOARD_FUTURE_MONTH_MESSAGES,
    BACKFILL_ALREADY_ACTIVE_MESSAGES, BACKFILL_NOT_ACTIVE_MESSAGES,
    DASHBOARD_INVALID_FORMAT_MESSAGES, BACKFILL_UNRESTRICTED_MESSAGES,
    BACKFILL_RESTRICTED_MESSAGES
)
from app.backfill import set_backfill, clear_backfill, get_backfill, set_unrestricted, clear_unrestricted, is_unrestricted

from config import (
    TELEGRAM_GET_UPDATES_ENDPOINT,
    TELEGRAM_GET_FILE_ENDPOINT,
    TELEGRAM_DOWNLOAD_FILE_ENDPOINT,
    TELEGRAM_CHAT_ID,
    RESULT_FILES_PATH
)


def is_message_photo(message) -> bool:
    return 'photo' in set(message.keys()) - {'message_id', 'from', 'chat', 'date'}


def get_updates(
    offset: int = None,
    chat_id: int = None,
    confirm_only: bool = False,
    timeout: int = 30
):
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


def download_file(file_id: str, message_id: int = None, date: int = None):
    file_path = requests.get(
        TELEGRAM_GET_FILE_ENDPOINT,
        params={
            'file_id': file_id
        }
    ).json().get('result').get('file_path')

    logger.info(f'Got {file_id}: {file_path}')

    file_name = file_path.split('/')[-1]
    file_endpoint = f'{TELEGRAM_DOWNLOAD_FILE_ENDPOINT}/{file_path}'

    os.makedirs(RESULT_FILES_PATH, exist_ok=True)
    with open(os.path.join(RESULT_FILES_PATH, file_name), "wb") as file:
        file.write(requests.get(file_endpoint).content)

    # Save metadata alongside the image for later processing
    meta_name = file_name.rsplit('.', 1)[0] + '.meta.json'
    metadata = {
        'message_id': message_id,
        'date': date,
    }
    
    backfill_data = get_backfill()
    if backfill_data:
        metadata['backfill'] = backfill_data
        
    with open(os.path.join(RESULT_FILES_PATH, meta_name), 'w') as meta_file:
        json.dump(metadata, meta_file)


def poll_and_download(timeout: int = 30) -> int:
    updates = get_updates(chat_id=int(TELEGRAM_CHAT_ID), timeout=timeout)

    if not updates:
        return None

    logger.info(f"Updates received: {updates}")

    has_photo = False
    for update in updates:
        message = update.get('message')
        if not message:
            continue
            
        text = message.get('text', '')
        if text.startswith('/backfill'):
            from_id = str(message.get('from', {}).get('id', ''))
            admins = get_chat_administrators()
            is_admin = from_id in admins
            
            if text == '/backfill unrestrict':
                if not is_admin:
                    send_message(random.choice(UNAUTHORIZED_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="UNAUTHORIZED")
                    continue
                set_unrestricted()
                send_message(random.choice(BACKFILL_UNRESTRICTED_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="BACKFILL_UNRESTRICTED")
                continue
                
            if text == '/backfill restrict':
                if not is_admin:
                    send_message(random.choice(UNAUTHORIZED_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="UNAUTHORIZED")
                    continue
                clear_unrestricted()
                send_message(random.choice(BACKFILL_RESTRICTED_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="BACKFILL_RESTRICTED")
                continue

            if not is_admin and not is_unrestricted():
                send_message(random.choice(UNAUTHORIZED_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="UNAUTHORIZED")
                continue
                
            if text == '/backfill end':
                if not get_backfill():
                    send_message(random.choice(BACKFILL_NOT_ACTIVE_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="BACKFILL_NOT_ACTIVE")
                    continue
                clear_backfill()
                send_message(random.choice(BACKFILL_END_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="BACKFILL_END")
            else:
                args = text.strip().split()
                if len(args) > 1:
                    date_str = args[1]
                    match1 = re.match(r'^(\d{4})/(\d{2})$', date_str)
                    match2 = re.match(r'^(\d{2})/(\d{4})$', date_str)
                    
                    if match1:
                        year = match1.group(1)
                        month = match1.group(2)
                    elif match2:
                        year = match2.group(2)
                        month = match2.group(1)
                    else:
                        send_message(random.choice(INVALID_BACKFILL_FORMAT_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="INVALID_BACKFILL_FORMAT")
                        continue
                        
                    if get_backfill():
                        send_message(random.choice(BACKFILL_ALREADY_ACTIVE_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="BACKFILL_ALREADY_ACTIVE")
                        continue
                        
                    set_backfill(year, month)
                    send_message(random.choice(BACKFILL_START_MESSAGES).format(month=month, year=year), reply_to_message_id=message.get('message_id'), msg_type="BACKFILL_START")
                else:
                    send_message(random.choice(INVALID_BACKFILL_FORMAT_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="INVALID_BACKFILL_FORMAT")
                        
        elif text.startswith(('/dashboard', '/dash')):
            from dashboard import generate_dashboard_image
            from datetime import datetime
            
            args = text.strip().split()
            target_year = None
            target_month = None
            
            if len(args) > 1:
                date_str = args[1]
                match1 = re.match(r'^(\d{4})/(\d{2})$', date_str)
                match2 = re.match(r'^(\d{2})/(\d{4})$', date_str)
                
                if match1:
                    target_year = int(match1.group(1))
                    target_month = int(match1.group(2))
                elif match2:
                    target_month = int(match2.group(1))
                    target_year = int(match2.group(2))
                else:
                    send_message(random.choice(DASHBOARD_INVALID_FORMAT_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="DASHBOARD_INVALID_FORMAT")
                    continue
                
                # Check if future month
                now = datetime.now()
                if target_year > now.year or (target_year == now.year and target_month > now.month):
                    send_message(random.choice(DASHBOARD_FUTURE_MONTH_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="DASHBOARD_FUTURE_MONTH")
                    continue
            
            send_message(random.choice(DASHBOARD_START_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="DASHBOARD_START")
            
            try:
                dash_path = generate_dashboard_image(target_year=target_year, target_month=target_month)
                if dash_path:
                    send_photo(dash_path, caption=random.choice(DASHBOARD_END_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="DASHBOARD_END")
                else:
                    send_message(random.choice(DASHBOARD_NO_DATA_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="DASHBOARD_NO_DATA")
            except Exception as e:
                logger.error(f"Error generating dashboard: {e}")
                from app.messages import ERROR_UNEXPECTED_MESSAGES
                send_message(random.choice(ERROR_UNEXPECTED_MESSAGES), reply_to_message_id=message.get('message_id'), msg_type="ERROR_UNEXPECTED")
                        
        elif is_message_photo(message):
            download_file(
                file_id=message.get('photo')[-1].get('file_id'),
                message_id=message.get('message_id'),
                date=message.get('date')
            )
            has_photo = True

    last_update = max([update.get('update_id') for update in updates]) if updates else None

    if has_photo:
        msg = random.choice(PROCESSING_MESSAGES)
        logger.info(f'Starting processing. Telegram offset read: {last_update}')
        send_message(msg, msg_type="PROCESSING")

    return last_update


def confirm_updates(last_update: int):
    if last_update:
        get_updates(
            offset=last_update,
            confirm_only=True
        )
