
import json
import random
import requests
import logging

logger = logging.getLogger(__name__)

from app.telegram import send_message
from app.messages import PROCESSING_MESSAGES

from config import (
    TELEGRAM_GET_UPDATES_ENDPOINT,
    TELEGRAM_GET_FILE_ENDPOINT,
    TELEGRAM_DOWNLOAD_FILE_ENDPOINT,
    TELEGRAM_CHAT_ID
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
        raise Exception('Failed to get updates!')

    elif not updates.get('ok', False) and confirm_only:
        return False

    elif updates.get('ok', False) and confirm_only:
        return True

    return [
        update for update in updates.get('result')
        if (not chat_id or update.get('message').get('chat').get('id') == chat_id)
        and update.get('message')
        and is_message_photo(update.get('message'))
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

    with open(f'results/{file_name}', "wb") as file:
        file.write(requests.get(file_endpoint).content)

    # Save metadata alongside the image for later processing
    meta_name = file_name.rsplit('.', 1)[0] + '.meta.json'
    metadata = {
        'message_id': message_id,
        'date': date,
    }
    with open(f'results/{meta_name}', 'w') as meta_file:
        json.dump(metadata, meta_file)


def poll_and_download(timeout: int = 30) -> int:
    updates = get_updates(chat_id=int(TELEGRAM_CHAT_ID), timeout=timeout)

    if not updates:
        return None

    logger.info(f"Updates received: {updates}")

    for update in updates:
        message = update.get('message')
        download_file(
            file_id=message.get('photo')[-1].get('file_id'),
            message_id=message.get('message_id'),
            date=message.get('date')
        )

    last_update = max([update.get('update_id') for update in updates]) if updates else None

    msg = random.choice(PROCESSING_MESSAGES)
    logger.info(f'Starting processing. Telegram offset read: {last_update}')
    send_message(msg)

    return last_update


def confirm_updates(last_update: int):
    if last_update:
        get_updates(
            offset=last_update,
            confirm_only=True
        )
