import json
import os
import random
import logging
import time
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


def process_file(image_path: str, date: str = None, reply_to: dict = None) -> Match:
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
        f"Here is a list of expected player names. If you see a name that has a minor OCR typo or closely resembles one of these, please use this EXACT spelling: {possible_names_str}. "
        "HOWEVER, do NOT forcefully match completely different names or different players (e.g. 'VictorB' is completely different from 'Victor Augusto'). If it's a different player, output exactly what is on the screen."
    )

    model_ladder = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    max_retries = 5
    
    last_error = None
    success = False
    result_text = ""
    overall_attempt = 0
    
    for model in model_ladder:
        for attempt in range(1, max_retries + 1):
            overall_attempt += 1
            try:
                logger.info(f"Analyzing image {image_path} with model '{model}' (attempt {attempt}/{max_retries})...")
                result = client.models.generate_content(
                    model=model,
                    contents=[uploaded_file, "\n\n", prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RESULT_SCHEMA
                    )
                )
                result_text = result.text
                success = True
                logger.info(f"Successfully processed image {image_path} with model '{model}'.")
                break
            except Exception as e:
                last_error = e
                err_str = str(e)
                is_rate_limit = any(c in err_str for c in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "ResourceExhausted", "quota"])
                wait_time = min(2 ** attempt, 32) if is_rate_limit else 1.5
                
                logger.warning(f"Attempt {attempt}/{max_retries} on model '{model}' failed for image {image_path}: {e}. Retrying in {wait_time}s...")
                
                if reply_to:
                    messenger = get_messenger()
                    from app.messages.system import FIRST_RETRY_MESSAGES, SUBSEQUENT_RETRY_MESSAGES
                    if overall_attempt == 1:
                        msg = random.choice(FIRST_RETRY_MESSAGES)
                    else:
                        msg = random.choice(SUBSEQUENT_RETRY_MESSAGES)
                    
                    messenger.send_message(
                        msg,
                        reply_to_message=reply_to,
                        msg_type="RETRY_BACKOFF"
                    )
                
                time.sleep(wait_time)
                
        if success:
            break

    # Delete the uploaded file from Google servers
    client.files.delete(name=uploaded_file.name)

    if not success:
        logger.error(f"Failed to process image {image_path} across models {model_ladder}. Last error: {last_error}")
        raise last_error

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
        # Read metadata (message_id, date, remoteJid, participant) from companion JSON
        metadata = read_image_metadata(image_path)
        message_id = metadata.get('message_id')
        reply_to = None
        if message_id:
            reply_to = {
                'id': message_id,
                'remoteJid': metadata.get('remoteJid'),
                'participant': metadata.get('participant')
            }

        # Parse date from media timestamp or use current date
        backfill_data = metadata.get('backfill')
        if backfill_data:
            date_str = f"01/{backfill_data['month']}/{backfill_data['year']}"
        else:
            media_date = metadata.get('date')
            if media_date:
                date_str = datetime.fromtimestamp(media_date).strftime('%d/%m/%Y')
            else:
                date_str = datetime.now().strftime('%d/%m/%Y')

        # Process the image with Gemini
        try:
            match = process_file(image_path, date=date_str, reply_to=reply_to)
            if not match:
                if reply_to:
                    messenger.send_message(
                        random.choice(INVALID_IMAGE_MESSAGES),
                        reply_to_message=reply_to,
                        msg_type="INVALID_IMAGE"
                    )
                from app.state_ignore import clear_ignore_player
                from app.state_erase import clear_erase
                clear_ignore_player()
                clear_erase()
                continue
        except Exception as e:
            err_str = str(e)
            logger.error(f"Full Gemini API exception: {err_str}")
            
            from app.state_ignore import clear_ignore_player
            from app.state_erase import clear_erase
            clear_ignore_player()
            clear_erase()
            
            if '429' in err_str or 'ResourceExhausted' in err_str or 'quota' in err_str.lower():
                logger.warning('Gemini API quota exhausted!')
                if reply_to:
                    messenger.send_message(
                        random.choice(ERROR_QUOTA_MESSAGES),
                        reply_to_message=reply_to,
                        msg_type="ERROR_QUOTA"
                    )
                break
            elif 'API key not valid' in err_str or 'API_KEY_INVALID' in err_str or '401' in err_str or 'UNAUTHENTICATED' in err_str:
                logger.error('Gemini API key is invalid or missing.')
                if reply_to:
                    messenger.send_message(
                        random.choice(ERROR_API_KEY_MESSAGES),
                        reply_to_message=reply_to,
                        msg_type="ERROR_API_KEY"
                    )
                break
            else:
                logger.error(f'Unexpected error processing image {image_path}')
                if reply_to:
                    messenger.send_message(
                        random.choice(ERROR_UNEXPECTED_MESSAGES),
                        reply_to_message=reply_to,
                        msg_type="ERROR_UNEXPECTED"
                    )
                continue

        from app.state_erase import get_erase, clear_erase
        from app.helpers import delete_match
        from app.messages.erase import ERASE_DELETED_MESSAGES, ERASE_NOT_FOUND_MESSAGES, ERASE_INACTIVE_MESSAGES

        if get_erase():
            deleted_count = delete_match(match.id)
            if deleted_count > 0:
                if reply_to:
                    msg_text = random.choice(ERASE_DELETED_MESSAGES).format(count=deleted_count)
                    messenger.send_message(
                        msg_text,
                        reply_to_message=reply_to,
                        msg_type="ERASE_DELETED"
                    )
                clear_erase()
            else:
                if reply_to:
                    messenger.send_message(
                        random.choice(ERASE_NOT_FOUND_MESSAGES),
                        reply_to_message=reply_to,
                        msg_type="ERASE_NOT_FOUND"
                    )
                clear_erase()
                
            if reply_to:
                messenger.send_message(
                    random.choice(ERASE_INACTIVE_MESSAGES),
                    reply_to_message=reply_to,
                    msg_type="ERASE_INACTIVE"
                )
            continue

        # Check for duplicates
        if match_exists(match.id):
            logger.info(f'Match {match.id} already exists, skipping.')
            
            from app.state_ignore import get_ignore_player, clear_ignore_player
            ignore_player = get_ignore_player()
            if ignore_player:
                from app.helpers import ignore_match_player
                from app.messages.ignore import IGNORE_RETROACTIVE_APPLIED_MESSAGES, IGNORE_MISSING_PLAYER_MESSAGES
                
                if any(record.player.name == ignore_player for record in match.records):
                    success = ignore_match_player(match.id, ignore_player)
                    if success and reply_to:
                        messenger.send_message(
                            random.choice(IGNORE_RETROACTIVE_APPLIED_MESSAGES).format(player_name=ignore_player),
                            reply_to_message=reply_to,
                            msg_type="IGNORE_RETROACTIVE_APPLIED"
                        )
                else:
                    if reply_to:
                        messenger.send_message(
                            random.choice(IGNORE_MISSING_PLAYER_MESSAGES).format(player_name=ignore_player),
                            reply_to_message=reply_to,
                            msg_type="IGNORE_MISSING_PLAYER"
                        )
                clear_ignore_player()
                continue
                
            if reply_to:
                messenger.send_message(
                    random.choice(DUPLICATE_MESSAGES),
                    reply_to_message=reply_to,
                    msg_type="DUPLICATE"
                )
            continue
            
        from app.state_ignore import get_ignore_player, clear_ignore_player
        ignore_player = get_ignore_player()
        if ignore_player:
            player_found = False
            for record in match.records:
                if record.player.name == ignore_player:
                    record.ignore_stats = True
                    player_found = True
            
            if player_found:
                from app.messages.ignore import IGNORE_APPLIED_MESSAGES
                if reply_to:
                    messenger.send_message(
                        random.choice(IGNORE_APPLIED_MESSAGES).format(player_name=ignore_player),
                        reply_to_message=reply_to,
                        msg_type="IGNORE_APPLIED"
                    )
            else:
                from app.messages.ignore import IGNORE_MISSING_PLAYER_MESSAGES
                if reply_to:
                    messenger.send_message(
                        random.choice(IGNORE_MISSING_PLAYER_MESSAGES).format(player_name=ignore_player),
                        reply_to_message=reply_to,
                        msg_type="IGNORE_MISSING_PLAYER"
                    )
            clear_ignore_player()

        player_stats = [
            {
                'player_name': record.player.name if record.player.name else record.player.id,
                'kills': record.kills,
                'damage': record.damage,
                'redeploys': record.redeploys,
                'is_clan_member': record.player.name is not None
            }
            for record in match.records if not getattr(record, 'ignore_stats', False)
        ]

        best_metric = evaluate_best_metric(player_stats)
        metric_message = best_metric.message if best_metric else None

        if metric_message:
            logger.info(f'Metric reply: {metric_message} (score: {best_metric.score})')

        matches.append((match, reply_to, metric_message))

    return matches


def process_all():
    results = process_files(RESULT_FILES_PATH)
    
    matches = [r[0] for r in results]
    last_reply_to = results[-1][1] if results else None
    
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
        return True, last_reply_to, best_message
    else:
        logger.info('There were no new matches to process')
        return False, None, None
