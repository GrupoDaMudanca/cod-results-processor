import json
import os
from config import RESULT_FILES_PATH
from app.backfill import get_backfill

def save_media_metadata(file_name: str, message_id: str, date: int):
    """Save metadata alongside the media file for later processing."""
    os.makedirs(RESULT_FILES_PATH, exist_ok=True)
    
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
