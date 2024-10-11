
import requests

from config import (
    TELEGRAM_GET_UPDATES_ENDPOINT,
    TELEGRAM_GET_FILE_ENDPOINT,
    TELEGRAM_DOWNLOAD_FILE_ENDPOINT,
    TELEGRAM_SEND_MESSAGE_ENDPOINT,
    TELEGRAM_CHAT_ID
)


def is_message_photo(message) -> bool:
    return 'photo' in set(message.keys()) - {'message_id', 'from', 'chat', 'date'}


def get_updates(
    offset: int = None,
    chat_id: int = None,
    confirm_only: bool = False
):
    if confirm_only and not offset:
        raise Exception('You must provide an offset to confirm')
    elif offset:
        offset += 1

    updates = requests.get(
        TELEGRAM_GET_UPDATES_ENDPOINT,
        params={
            'offset': offset
        }
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


def download_file(file_id: str):
    file_path = requests.get(
        TELEGRAM_GET_FILE_ENDPOINT,
        params={
            'file_id': file_id
        }
    ).json().get('result').get('file_path')

    print(f'Got {file_id}: {file_path}')

    file_name = file_path.split('/')[-1]
    file_endpoint = f'{TELEGRAM_DOWNLOAD_FILE_ENDPOINT}/{file_path}'

    with open(f'results/{file_name}', "wb") as file:
        file.write(requests.get(file_endpoint).content)


def send_confirmation_message(message: str):
    return requests.get(
        TELEGRAM_SEND_MESSAGE_ENDPOINT,
        params={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message
        }
    )


updates = get_updates()

if not updates:
    print('There are no updates')
    exit(0)

print(updates)

for update in updates:
    download_file(update.get('message').get('photo')[-1].get('file_id'))

last_update = max([update.get('update_id') for update in updates]) if updates else None

get_updates(
    offset=last_update,
    confirm_only=True
)

response = send_confirmation_message(f'Ei! Estou começando a processar até a mensagem de offset {last_update}')

print(response.json())
