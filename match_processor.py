import json
import os
import random
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

from app.helpers import read_new_match, write_matches, match_exists
from app.match import Match
from app.metrics import evaluate_best_metric
from app.messengers import get_messenger
from app.messages import (
    DUPLICATE_MESSAGES,
    ERROR_QUOTA_MESSAGES,
    ERROR_API_KEY_MESSAGES,
    ERROR_UNEXPECTED_MESSAGES,
    INVALID_IMAGE_MESSAGES,
)

from config import (
    GEMINI_API_KEY,
    GEMINI_DESIRED_MODEL,
    RESULT_FILETYPES,
    RESULT_FILES_PATH,
    PLAYER_NAMES_FILE_PATH
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
        "required": ["raw_player_name", "score", "kills", "assists", "redeploys", "damage"]
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
    logger.info(f'Processing {image_path}')

    uploaded_file = client.files.upload(file=image_path)
    logger.info(f'Uploaded file: {uploaded_file.name}')

    possible_names_str = ""
    if os.path.exists(PLAYER_NAMES_FILE_PATH):
        with open(PLAYER_NAMES_FILE_PATH, 'r') as f:
            clan_mapping = json.load(f)
            possible_names = []
            for aliases in clan_mapping.values():
                possible_names.extend(aliases)
            possible_names_str = ", ".join(possible_names)

    prompt = (
        "Read this image for me. "
        "CRITICAL INSTRUCTION: If the image is NOT a Call of Duty match scoreboard/results screen, you must return an empty array []. "
        "Disconsider the line showing the squad's total points. "
        "IMPORTANT: Do not confuse 'Eliminações' with 'Kills'. In this game, 'Eliminações' = Kills + Assists. "
        "Therefore, map the column 'Baixas' to the 'kills' field, and completely ignore the 'Eliminações' column. "
        f"Here is a list of expected player names. If you see a name that closely resembles one of these, please use this EXACT spelling: {possible_names_str}"
    )

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

    logger.info(f"AI identified stats:\n{result_text}")

    match_data = json.loads(result_text)
    
    if not match_data:
        logger.warning(f"No match data found in image {image_path}. AI returned empty array.")
        return None

    match = read_new_match(match_data, date=date)

    return match


def process_files(root_path: str) -> List[Match]:
    messenger = get_messenger()
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
        backfill_data = metadata.get('backfill')
        if backfill_data:
            date_str = f"01/{backfill_data['month']}/{backfill_data['year']}"
        else:
            telegram_date = metadata.get('date')
            if telegram_date:
                date_str = datetime.fromtimestamp(telegram_date).strftime('%d/%m/%Y')
            else:
                date_str = datetime.now().strftime('%d/%m/%Y')

        # Process the image with Gemini
        try:
            match = process_file(image_path, date=date_str)
            if not match:
                if message_id:
                    messenger.send_message(
                        random.choice(INVALID_IMAGE_MESSAGES),
                        reply_to_message_id=message_id,
                        msg_type="INVALID_IMAGE"
                    )
                continue
        except Exception as e:
            err_str = str(e)
            logger.error(f"Full Gemini API exception: {err_str}")
            if '429' in err_str or 'ResourceExhausted' in err_str or 'quota' in err_str.lower():
                logger.warning('Gemini API quota exhausted!')
                messenger.send_message(
                    random.choice(ERROR_QUOTA_MESSAGES),
                    reply_to_message_id=message_id,
                    msg_type="ERROR_QUOTA"
                )
                break
            elif 'API key not valid' in err_str or 'API_KEY_INVALID' in err_str or '401' in err_str or 'UNAUTHENTICATED' in err_str:
                logger.error('Gemini API key is invalid or missing.')
                messenger.send_message(
                    random.choice(ERROR_API_KEY_MESSAGES),
                    reply_to_message_id=message_id,
                    msg_type="ERROR_API_KEY"
                )
                break
            else:
                logger.error(f'Unexpected error processing image {image_path}')
                messenger.send_message(
                    random.choice(ERROR_UNEXPECTED_MESSAGES),
                    reply_to_message_id=message_id,
                    msg_type="ERROR_UNEXPECTED"
                )
                continue

        # Check for duplicates
        if match_exists(match.id):
            logger.info(f'Match {match.id} already exists, skipping.')
            if message_id:
                messenger.send_message(
                    random.choice(DUPLICATE_MESSAGES),
                    reply_to_message_id=message_id,
                    msg_type="DUPLICATE"
                )
            continue

        player_stats = [
            {
                'player_name': record.player.name if record.player.name else record.player.id,
                'kills': record.kills,
                'damage': record.damage,
                'redeploys': record.redeploys,
                'is_clan_member': record.player.name is not None
            }
            for record in match.records
        ]

        best_metric = evaluate_best_metric(player_stats)
        metric_message = best_metric.message if best_metric else None

        if metric_message:
            logger.info(f'Metric reply: {metric_message} (score: {best_metric.score})')

        matches.append((match, message_id, metric_message))

    return matches


def process_all():
    results = process_files(RESULT_FILES_PATH)
    
    matches = [r[0] for r in results]
    last_message_id = results[-1][1] if results else None
    
    # Get the highest scored metric message across all processed images in this batch
    best_message = None
    if results:
        # We just pick the last non-empty message for simplicity, or the first one we find
        for r in reversed(results):
            if r[2]:
                best_message = r[2]
                break

    if matches:
        write_matches(matches)
        return True, last_message_id, best_message
    else:
        logger.info('There were no new matches to process')
        return False, None, None
