import os
import json
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

STATE_FILE_PATH = os.getenv("CRON_STATE_FILE_PATH", ".data/cron_state.json")
TZ = os.getenv("TZ", "America/Sao_Paulo")

def _get_current_date_str():
    try:
        timezone = pytz.timezone(TZ)
    except pytz.UnknownTimeZoneError:
        timezone = pytz.UTC
    now = datetime.now(timezone)
    return now.strftime("%Y-%m-%d")

def get_cron_state():
    """Reads the state file. Resets it if it's a new day."""
    current_date = _get_current_date_str()
    
    if not os.path.exists(STATE_FILE_PATH):
        return {"date": current_date, "sent_jobs": []}
        
    try:
        with open(STATE_FILE_PATH, 'r') as f:
            state = json.load(f)
            
        if state.get("date") != current_date:
            # New day, reset the state
            logger.info("New day detected in cron state. Resetting sent jobs.")
            return {"date": current_date, "sent_jobs": []}
            
        return state
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read cron state file: {e}")
        return {"date": current_date, "sent_jobs": []}

def mark_job_sent(job_id):
    """Marks a job as sent for the current day and saves to JSON."""
    state = get_cron_state()
    
    if job_id not in state["sent_jobs"]:
        state["sent_jobs"].append(job_id)
        
    try:
        os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump(state, f, indent=4)
        logger.info(f"Marked job '{job_id}' as sent for {state['date']}")
    except IOError as e:
        logger.error(f"Failed to save cron state file: {e}")
