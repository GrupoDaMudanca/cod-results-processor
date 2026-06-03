import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import CRON_CITATION_SCHEDULE, TZ
from app.citations import get_random_citation
from app.messengers import get_messenger
from app.messages import CITATION_EMPTY_MESSAGES

logger = logging.getLogger(__name__)

def send_daily_citation():
    """Fetches a citation and sends it to the group."""
    logger.info("Executing daily citation cron job...")
    citation = get_random_citation()
    messenger = get_messenger()
    
    if citation:
        messenger.send_message(f"📖 *Pérola do Dia:*\n\n{citation}", msg_type="CITATION_DAILY")
    else:
        logger.info("No citations available to send.")
        # User specified: "a menos que não tenha nenhuma citação pra enviar, ai ele n deve enviar nd"
        # Oh wait, the user said "se ele não tiver nenhuma, mande uma msg dizendo q não tem" for the /citation command.
        # But for the cron: "a menos que não tenha nenhuma citação pra enviar, ai ele n deve enviar nd".
        # So for cron, we don't send the empty message. We just do nothing!
        pass

def start_scheduler():
    """Initializes and starts the APScheduler with configured jobs."""
    try:
        timezone = pytz.timezone(TZ)
    except pytz.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone {TZ}. Falling back to UTC.")
        timezone = pytz.UTC

    scheduler = BackgroundScheduler(timezone=timezone)
    
    try:
        trigger = CronTrigger.from_crontab(CRON_CITATION_SCHEDULE, timezone=timezone)
    except ValueError as e:
        logger.error(f"Invalid cron format: {CRON_CITATION_SCHEDULE}. Error: {e}. Citation cron disabled.")
        return
    
    scheduler.add_job(send_daily_citation, trigger)
    scheduler.start()
    logger.info(f"Cron scheduler started. Citation job scheduled with '{CRON_CITATION_SCHEDULE}' in {timezone}")
