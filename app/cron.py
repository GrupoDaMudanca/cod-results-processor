import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import CRON_CITATION_SCHEDULE, CRON_WIN_CHECK_SCHEDULE, CRON_MORNING_MOTIVATION_SCHEDULE, TZ, LATEST_OUTPUT_FILE_PATH
from app.citations import get_random_citation
from app.messengers import get_messenger
from app.messages import CITATION_EMPTY_MESSAGES, WIN_CHECK_SINGLE_WIN_MESSAGES, WIN_CHECK_MULTIPLE_WINS_MESSAGES, WIN_CHECK_FAIL_MESSAGES, WIN_CHECK_MULTIPLE_DAYS_FAIL_MESSAGES, MORNING_MOTIVATION_MESSAGES
import pandas as pd
import os
from datetime import datetime, timedelta

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
        pass

def send_daily_win_check():
    """Checks if there was a win today and sends an acidic message."""
    logger.info("Executing daily win check cron job...")
    messenger = get_messenger()
    
    wins_today = 0
    days_without_win = 1
    if os.path.exists(LATEST_OUTPUT_FILE_PATH) and os.stat(LATEST_OUTPUT_FILE_PATH).st_size > 0:
        try:
            df = pd.read_csv(LATEST_OUTPUT_FILE_PATH)
            if 'date' in df.columns:
                try:
                    timezone = pytz.timezone(TZ)
                except pytz.UnknownTimeZoneError:
                    timezone = pytz.UTC
                    
                today = datetime.now(timezone)
                today_str = today.strftime('%d/%m/%Y')
                today_df = df[df['date'] == today_str]
                wins_today = today_df['match_id'].nunique()
                
                if wins_today == 0:
                    df['parsed_date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
                    last_win_date = df['parsed_date'].max()
                    if pd.notna(last_win_date):
                        days_without_win = (today.replace(tzinfo=None) - last_win_date).days
        except Exception as e:
            logger.error(f"Failed to read CSV for win check: {e}")
            
    if wins_today == 1:
        messenger.send_message(random.choice(WIN_CHECK_SINGLE_WIN_MESSAGES), msg_type="WIN_CHECK_SINGLE")
    elif wins_today > 1:
        msg = random.choice(WIN_CHECK_MULTIPLE_WINS_MESSAGES).replace("{count}", str(wins_today))
        messenger.send_message(msg, msg_type="WIN_CHECK_MULTIPLE")
    else:
        if days_without_win > 1:
            msg = random.choice(WIN_CHECK_MULTIPLE_DAYS_FAIL_MESSAGES).replace("{days}", str(days_without_win))
            messenger.send_message(msg, msg_type="WIN_CHECK_MULTIPLE_FAIL")
        else:
            messenger.send_message(random.choice(WIN_CHECK_FAIL_MESSAGES), msg_type="WIN_CHECK_FAIL")

def send_morning_motivation():
    """Checks if there were no wins yesterday and sends a 'motivational' message."""
    logger.info("Executing morning motivation cron job...")
    messenger = get_messenger()
    
    wins_yesterday = 0
    if os.path.exists(LATEST_OUTPUT_FILE_PATH) and os.stat(LATEST_OUTPUT_FILE_PATH).st_size > 0:
        try:
            df = pd.read_csv(LATEST_OUTPUT_FILE_PATH)
            if 'date' in df.columns:
                try:
                    timezone = pytz.timezone(TZ)
                except pytz.UnknownTimeZoneError:
                    timezone = pytz.UTC
                    
                yesterday = datetime.now(timezone) - timedelta(days=1)
                yesterday_str = yesterday.strftime('%d/%m/%Y')
                yesterday_df = df[df['date'] == yesterday_str]
                wins_yesterday = yesterday_df['match_id'].nunique()
        except Exception as e:
            logger.error(f"Failed to read CSV for morning motivation: {e}")
            
    if wins_yesterday == 0:
        messenger.send_message(random.choice(MORNING_MOTIVATION_MESSAGES), msg_type="MORNING_MOTIVATION")
    else:
        logger.info("They won yesterday, so no motivation needed today.")

def start_scheduler():
    """Initializes and starts the APScheduler with configured jobs."""
    try:
        timezone = pytz.timezone(TZ)
    except pytz.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone {TZ}. Falling back to UTC.")
        timezone = pytz.UTC

    scheduler = BackgroundScheduler(timezone=timezone)
    
    try:
        trigger_citation = CronTrigger.from_crontab(CRON_CITATION_SCHEDULE, timezone=timezone)
        scheduler.add_job(send_daily_citation, trigger_citation)
        logger.info(f"Citation job scheduled with '{CRON_CITATION_SCHEDULE}' in {timezone}")
    except ValueError as e:
        logger.error(f"Invalid cron format: {CRON_CITATION_SCHEDULE}. Error: {e}. Citation cron disabled.")
        
    try:
        trigger_win = CronTrigger.from_crontab(CRON_WIN_CHECK_SCHEDULE, timezone=timezone)
        scheduler.add_job(send_daily_win_check, trigger_win)
        logger.info(f"Win check job scheduled with '{CRON_WIN_CHECK_SCHEDULE}' in {timezone}")
    except ValueError as e:
        logger.error(f"Invalid cron format: {CRON_WIN_CHECK_SCHEDULE}. Error: {e}. Win check cron disabled.")
    
    try:
        trigger_morning = CronTrigger.from_crontab(CRON_MORNING_MOTIVATION_SCHEDULE, timezone=timezone)
        scheduler.add_job(send_morning_motivation, trigger_morning)
        logger.info(f"Morning motivation job scheduled with '{CRON_MORNING_MOTIVATION_SCHEDULE}' in {timezone}")
    except ValueError as e:
        logger.error(f"Invalid cron format: {CRON_MORNING_MOTIVATION_SCHEDULE}. Error: {e}. Morning motivation cron disabled.")

    scheduler.start()
    logger.info("Cron scheduler started.")
