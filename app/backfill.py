import json
import os
import logging

logger = logging.getLogger(__name__)

DATA_DIR = '.data'
BACKFILL_FILE_PATH = os.path.join(DATA_DIR, 'backfill.json')
UNRESTRICT_FILE_PATH = os.path.join(DATA_DIR, 'unrestrict.json')

def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def set_backfill(year: str, month: str):
    """Activates backfill mode by setting the month and year."""
    _ensure_data_dir()
    data = {
        'active': True,
        'year': year,
        'month': month
    }
    with open(BACKFILL_FILE_PATH, 'w') as f:
        json.dump(data, f)
    logger.info(f"Backfill activated for: {month}/{year}")

def get_backfill():
    """Returns a dictionary with backfill month and year if active."""
    if not os.path.exists(BACKFILL_FILE_PATH):
        return None
    try:
        with open(BACKFILL_FILE_PATH, 'r') as f:
            data = json.load(f)
            if data.get('active'):
                return data
    except Exception as e:
        logger.error(f"Error reading backfill file: {e}")
    return None

def clear_backfill():
    """Deactivates backfill mode."""
    if os.path.exists(BACKFILL_FILE_PATH):
        os.remove(BACKFILL_FILE_PATH)
        logger.info("Backfill deactivated.")

def set_unrestricted():
    _ensure_data_dir()
    with open(UNRESTRICT_FILE_PATH, 'w') as f:
        json.dump({'unrestricted': True}, f)
    logger.info("Backfill unrestricted for all users.")

def clear_unrestricted():
    if os.path.exists(UNRESTRICT_FILE_PATH):
        os.remove(UNRESTRICT_FILE_PATH)
        logger.info("Backfill restricted to admins.")

def is_unrestricted():
    return os.path.exists(UNRESTRICT_FILE_PATH)
