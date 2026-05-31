import json
import os
import random
from datetime import datetime
from typing import List

from app.helpers import read_new_match, write_matches, match_exists
from app.match import Match
from app.metrics import evaluate_best_metric
from app.telegram import send_message

from config import (
    GEMINI_API_KEY,
    GEMINI_DESIRED_MODEL,
    RESULT_FILETYPES,
    RESULT_FILES_PATH
)

from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_API_KEY)

# Structured schema for Gemini response
RESULT_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "raw_player_name": {
                "type": "STRING",
                "description": "Nome ou Name do jogador"
            },
            "score": {
                "type": "INTEGER",
                "description": "Pontuação ou Score"
            },
            "eliminations": {
                "type": "INTEGER",
                "description": "Eliminações ou Eliminations"
            },
            "kills": {
                "type": "INTEGER",
                "description": "Baixas ou Kills"
            },
            "assists": {
                "type": "INTEGER",
                "description": "Assist. ou Assists"
            },
            "redeploys": {
                "type": "INTEGER",
                "description": "Remobilizações ou Redeploys"
            },
            "damage": {
                "type": "INTEGER",
                "description": "Dano ou Damage"
            }
        },
        "required": ["raw_player_name", "score", "eliminations", "kills", "assists", "redeploys", "damage"]
    }
}


def read_image_metadata(image_path: str) -> dict:
    """Read companion .meta.json file for a downloaded image."""
    base_name = image_path.rsplit('.', 1)[0]
    meta_path = base_name + '.meta.json'

    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            return json.load(f)

    return {}


def process_file(image_path: str, date: str = None) -> Match:
    print(f'Processing {image_path}')

    uploaded_file = client.files.upload(file=image_path)
    print(f'Uploaded file: {uploaded_file.name}')

    prompt = "Read this image for me. Disconsider the line showing the squad's total points."

    result = client.models.generate_content(
        model=GEMINI_DESIRED_MODEL,
        contents=[uploaded_file, "\n\n", prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RESULT_SCHEMA
        )
    )

    # Delete the uploaded file from Google servers
    client.files.delete(name=uploaded_file.name)

    result_text = result.text

    print(result_text)

    match_data = json.loads(result_text)

    match = read_new_match(match_data, date=date)

    return match


def process_files(root_path: str) -> List[Match]:
    full_base_path = os.path.join(os.getcwd(), root_path)

    image_paths = [
        os.path.join(full_base_path, path) for path in
        os.listdir(full_base_path)
        if any(filetype in path for filetype in RESULT_FILETYPES)
    ]

    if not image_paths:
        return []

    matches = []

    for image_path in image_paths:
        # Read metadata (message_id, date) from companion JSON
        metadata = read_image_metadata(image_path)
        message_id = metadata.get('message_id')

        # Parse date from Telegram timestamp or use current date
        telegram_date = metadata.get('date')
        if telegram_date:
            date_str = datetime.fromtimestamp(telegram_date).strftime('%d/%m/%Y')
        else:
            date_str = datetime.now().strftime('%d/%m/%Y')

        # Process the image with Gemini
        try:
            match = process_file(image_path, date=date_str)
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'ResourceExhausted' in err_str or 'quota' in err_str.lower():
                print('Gemini API quota exhausted!')
                send_message(
                    'Ei bixo, eu tô meio liso ó, fiquei sem tokens 😅 tenta mandar dnv depois',
                    reply_to_message_id=message_id
                )
                break
            elif 'API key not valid' in err_str or 'API_KEY_INVALID' in err_str:
                print('Gemini API key is invalid or missing.')
                send_message(
                    'Vixe macho, perdi meu cérebro 🤡 Tem como tu me dar uma ajudinha?',
                    reply_to_message_id=message_id
                )
                break
            raise e

        # Check for duplicates
        if match_exists(match.id):
            print(f'Match {match.id} already exists, skipping.')
            if message_id:
                DUPLICATE_MESSAGES = [
                    "ei keres leyte, já foi processado essa imagem",
                    "Aí dento, tá mandando print repetido pra farmar ponto é? 🤡",
                    "Oxe, essa partida aí eu já contei faz é tempo! Tá achando que eu sou besta?",
                    "Print duplicada detectada! Pelo visto alguém tá tentando inflar os stats... 👀",
                    "Vixe, essa imagem aí já passou pelo tribunal. Manda outra!",
                    "Repetido! Se continuar mandando print velho vou zerar teus pontos 💀",
                    "Já li essa meu chapa! Tenta a sorte na próxima. 🕵️‍♂️"
                ]
                send_message(
                    random.choice(DUPLICATE_MESSAGES),
                    reply_to_message_id=message_id
                )
            continue

        # Evaluate metrics and send zoeira reply
        player_stats = [
            {
                'player_name': record.player.name or record.player.id,
                'kills': record.kills,
                'damage': record.damage,
                'redeploys': record.redeploys,
            }
            for record in match.records
        ]

        best_metric = evaluate_best_metric(player_stats)

        if best_metric and best_metric.message:
            print(f'Metric reply: {best_metric.message} (score: {best_metric.score})')
            if message_id:
                send_message(
                    best_metric.message,
                    reply_to_message_id=message_id
                )
            else:
                send_message(best_metric.message)

        matches.append(match)

    return matches


matches = process_files(RESULT_FILES_PATH)

if matches:
    write_matches(matches)
else:
    print('There were no new matches to process')
