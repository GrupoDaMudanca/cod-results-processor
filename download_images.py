
import json
import random
import requests

from app.telegram import send_message

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


def download_file(file_id: str, message_id: int = None, date: int = None):
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

    # Save metadata alongside the image for later processing
    meta_name = file_name.rsplit('.', 1)[0] + '.meta.json'
    metadata = {
        'message_id': message_id,
        'date': date,
    }
    with open(f'results/{meta_name}', 'w') as meta_file:
        json.dump(metadata, meta_file)


updates = get_updates()

if not updates:
    print('There are no updates')
    exit(0)

print(updates)

for update in updates:
    message = update.get('message')
    download_file(
        file_id=message.get('photo')[-1].get('file_id'),
        message_id=message.get('message_id'),
        date=message.get('date')
    )

last_update = max([update.get('update_id') for update in updates]) if updates else None

get_updates(
    offset=last_update,
    confirm_only=True
)

PROCESSING_MESSAGES = [
    "Aí dento! Bora ver quem carregou e quem foi carregado nessas partidas... 🧐",
    "Cheguei pro expediente! Puxando as prints pra analisar o desastre... 📊",
    "Ei macho, guenta aí que já tô lendo essas imagens pra julgar o desempenho de vocês 🤡",
    "Ajeitando os óculos aqui pra ler essas tabelas... vamos ver quem foi o peso morto de hoje 🪨",
    "Pera lá, pera lá! Baixando as fotos do tribunal. Já dou o veredito... 👨‍⚖️",
    "Limpando o cache do cérebro pra processar essas partidas... 🧠",
    "Ixe, lá vem mais choro! Deixa eu ver quem foi o MVP do gulag dessa vez... ☠️"
]

msg = random.choice(PROCESSING_MESSAGES)
print(f'Começando a processar. Offset do Telegram lido: {last_update}')
response = send_message(msg)

print(response)
