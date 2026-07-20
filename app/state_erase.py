import json
import os
import logging

logger = logging.getLogger(__name__)

DATA_DIR = '.data'
ERASE_FILE_PATH = os.path.join(DATA_DIR, 'erase.json')

def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def set_erase():
    """Activates erase mode."""
    _ensure_data_dir()
    data = {
        'active': True
    }
    with open(ERASE_FILE_PATH, 'w') as f:
        json.dump(data, f)
    logger.info("Erase mode activated.")

def get_erase() -> bool:
    """Returns True if erase mode is active, False otherwise."""
    if not os.path.exists(ERASE_FILE_PATH):
        return False
    try:
        with open(ERASE_FILE_PATH, 'r') as f:
            data = json.load(f)
            return bool(data.get('active', False))
    except Exception as e:
        logger.error(f"Error reading erase file: {e}")
    return False

def clear_erase():
    """Deactivates erase mode."""
    if os.path.exists(ERASE_FILE_PATH):
        os.remove(ERASE_FILE_PATH)
        logger.info("Erase mode deactivated.")
