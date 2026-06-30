import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import CRON_CITATION_SCHEDULE, CRON_WIN_CHECK_SCHEDULE, CRON_MORNING_MOTIVATION_SCHEDULE, CRON_MONTHLY_AWARDS_SCHEDULE, CRON_END_OF_MONTH_HYPE_SCHEDULE, TZ, LATEST_OUTPUT_FILE_PATH
from app.citations import get_random_citation
from app.messengers import get_messenger
from app.messages import CITATION_EMPTY_MESSAGES, WIN_CHECK_SINGLE_WIN_MESSAGES, WIN_CHECK_MULTIPLE_WINS_MESSAGES, WIN_CHECK_FAIL_MESSAGES, WIN_CHECK_MULTIPLE_DAYS_FAIL_MESSAGES, WIN_CHECK_EXTREME_FAIL_MESSAGES, MORNING_MOTIVATION_MESSAGES, MORNING_EXTREME_MOTIVATION_MESSAGES, MONTH_END_HYPE_MESSAGES, MONTHLY_AWARD_TEMPLATES, MONTHLY_AWARD_INTRO_MESSAGES, MONTHLY_AWARD_OUTRO_MESSAGES, MONTH_END_HYPE_OUTRO_MESSAGES
import pandas as pd
import os
import calendar
from datetime import datetime, timedelta

from app.state import mark_job_sent, get_cron_state

logger = logging.getLogger(__name__)

def send_daily_citation():
    """Fetches a citation and sends it to the group."""
    logger.info("Executing daily citation cron job...")
    citation = get_random_citation()
    messenger = get_messenger()
    
    if citation:
        res = messenger.send_message(f"📖 *Pérola do Dia:*\n\n{citation}", msg_type="CITATION_DAILY")
        if res:
            mark_job_sent("citation")
    else:
        logger.info("No citations available to send.")
        mark_job_sent("citation")

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
        res = messenger.send_message(random.choice(WIN_CHECK_SINGLE_WIN_MESSAGES), msg_type="WIN_CHECK_SINGLE")
    elif wins_today > 1:
        msg = random.choice(WIN_CHECK_MULTIPLE_WINS_MESSAGES).replace("{count}", str(wins_today))
        res = messenger.send_message(msg, msg_type="WIN_CHECK_MULTIPLE")
    else:
        if days_without_win >= 3:
            msg = random.choice(WIN_CHECK_EXTREME_FAIL_MESSAGES).replace("{days}", str(days_without_win))
            res = messenger.send_message(msg, msg_type="WIN_CHECK_EXTREME_FAIL")
        elif days_without_win > 1:
            msg = random.choice(WIN_CHECK_MULTIPLE_DAYS_FAIL_MESSAGES).replace("{days}", str(days_without_win))
            res = messenger.send_message(msg, msg_type="WIN_CHECK_MULTIPLE_FAIL")
        else:
            res = messenger.send_message(random.choice(WIN_CHECK_FAIL_MESSAGES), msg_type="WIN_CHECK_FAIL")
            
    if res:
        mark_job_sent("win_check")

def send_morning_motivation():
    """Checks if there were no wins yesterday and sends a 'motivational' message."""
    logger.info("Executing morning motivation cron job...")
    messenger = get_messenger()
    
    wins_yesterday = 0
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
                    
                now = datetime.now(timezone)
                yesterday = now - timedelta(days=1)
                
                yesterday_str = yesterday.strftime('%d/%m/%Y')
                today_str = now.strftime('%d/%m/%Y')
                
                yesterday_df = df[df['date'] == yesterday_str]
                wins_yesterday = yesterday_df['match_id'].nunique()
                
                today_df = df[df['date'] == today_str]
                wins_today = today_df['match_id'].nunique()
                
                if wins_yesterday == 0 and wins_today == 0:
                    df['parsed_date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
                    last_win_date = df['parsed_date'].max()
                    if pd.notna(last_win_date):
                        days_without_win = (now.replace(tzinfo=None) - last_win_date).days
        except Exception as e:
            logger.error(f"Failed to read CSV for morning motivation: {e}")
            
    if wins_today > 0:
        logger.info("They already won today, skipping morning motivation.")
        return

    res = False
    if wins_yesterday == 0:
        if days_without_win >= 4:
            msg = random.choice(MORNING_EXTREME_MOTIVATION_MESSAGES)
            res = messenger.send_message(msg, msg_type="MORNING_EXTREME_MOTIVATION")
        else:
            res = messenger.send_message(random.choice(MORNING_MOTIVATION_MESSAGES), msg_type="MORNING_MOTIVATION")
    else:
        logger.info("They won yesterday, so no motivation needed today.")
        res = True
        
    if res:
        mark_job_sent("morning_motivation")

def send_monthly_awards():
    """Sends the monthly dashboard and awards on the 1st of the month."""
    logger.info("Executing monthly awards cron job...")
    messenger = get_messenger()
    
    try:
        timezone = pytz.timezone(TZ)
    except pytz.UnknownTimeZoneError:
        timezone = pytz.UTC
        
    now = datetime.now(timezone)
    first_day_this_month = now.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)
    
    from dashboard import generate_dashboard_image, get_monthly_highlights, load_data
    dashboard_path = generate_dashboard_image(start_date=first_day_prev_month, end_date=last_day_prev_month)
    
    df = load_data(start_date=first_day_prev_month, end_date=last_day_prev_month)
    if df.empty or dashboard_path is None:
        logger.warning("No data for last month to generate awards.")
        mark_job_sent("monthly_awards")
        return
        
    highlights = get_monthly_highlights(df)
    
    PT_MONTHS = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    month_name = PT_MONTHS[first_day_prev_month.month]
    year = first_day_prev_month.year
    messenger.send_photo(dashboard_path, caption=None, msg_type="MONTHLY_DASHBOARD")
    
    intro_msg = random.choice(MONTHLY_AWARD_INTRO_MESSAGES)
    text_parts = [
        "*🏆 PREMIAÇÕES DO MÊS 🏆*",
        f"_{intro_msg}_"
    ]
    
    for key, templates in MONTHLY_AWARD_TEMPLATES.items():
        template = random.choice(templates)
        top_df = highlights.get(key)
        if top_df is not None and not top_df.empty:
            first_row = top_df.iloc[0]
            name = first_row['player_name']
            val = 0
            if key == 'top_kills': val = int(first_row['kills'])
            elif key == 'top_avg_kills': val = f"{first_row['kill_avg']:.1f}"
            elif key == 'top_wins': val = int(first_row['wins'])
            elif key == 'top_high_redeploys': val = f"{first_row['redeploy_avg']:.1f}"
            elif key == 'top_waste_bullet': val = f"{first_row['damage_avg']:.0f}"
            elif key == 'top_kill_stealer': val = f"{first_row['dmg_per_kill']:.0f}"
            elif key == 'top_low_redeploys': val = f"{first_row['redeploy_avg']:.1f}"
            elif key == 'top_soft_puncher': val = f"{first_row['assist_avg']:.1f}"
            elif key == 'top_low_kills': val = f"{first_row['kill_avg']:.1f}"
            
            text_parts.append("- " + template.format(name=name, val=val))
            
    
    outro_msg = random.choice(MONTHLY_AWARD_OUTRO_MESSAGES)
    text_parts.append(f"_{outro_msg}_")
            
    final_text = "\n\n".join(text_parts)
    res = messenger.send_message(final_text, msg_type="MONTHLY_AWARDS")
    if res:
        mark_job_sent("monthly_awards")

def send_month_end_hype():
    """Sends a hype message in the last 5 days of the month."""
    logger.info("Executing month end hype cron job...")
    
    try:
        timezone = pytz.timezone(TZ)
    except pytz.UnknownTimeZoneError:
        timezone = pytz.UTC
        
    now = datetime.now(timezone)
    last_day_of_month = calendar.monthrange(now.year, now.month)[1]
    days_left = (last_day_of_month - now.day) + 1
    
    if days_left <= 5:
        messenger = get_messenger()
        if days_left == 1:
            days_str = "algumas horas"
            title = "*ÚLTIMAS HORAS!*"
        else:
            days_str = f"{days_left} dias"
            title = f"*FALTAM {days_left} DIAS!*"
            
        intro_msg = random.choice(MONTH_END_HYPE_MESSAGES).replace("{days}", days_str)
        text_parts = [
            title,
            f"_{intro_msg}_"
        ]
        
        from dashboard import generate_dashboard_image, get_monthly_highlights, load_data
        first_day_curr_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dashboard_path = generate_dashboard_image(start_date=first_day_curr_month, end_date=now)
            
        if dashboard_path:
            messenger.send_photo(dashboard_path, caption=None, msg_type="MONTH_END_HYPE_DASHBOARD")
            
        df = load_data(start_date=first_day_curr_month, end_date=now)
        
        if not df.empty:
            highlights = get_monthly_highlights(df)
            for key, templates in MONTHLY_AWARD_TEMPLATES.items():
                template = random.choice(templates)
                top_df = highlights.get(key)
                if top_df is not None and not top_df.empty:
                    first_row = top_df.iloc[0]
                    name = first_row['player_name']
                    val = 0
                    if key == 'top_kills': val = int(first_row['kills'])
                    elif key == 'top_avg_kills': val = f"{first_row['kill_avg']:.1f}"
                    elif key == 'top_wins': val = int(first_row['wins'])
                    elif key == 'top_high_redeploys': val = f"{first_row['redeploy_avg']:.1f}"
                    elif key == 'top_waste_bullet': val = f"{first_row['damage_avg']:.0f}"
                    elif key == 'top_kill_stealer': val = f"{first_row['dmg_per_kill']:.0f}"
                    elif key == 'top_low_redeploys': val = f"{first_row['redeploy_avg']:.1f}"
                    elif key == 'top_soft_puncher': val = f"{first_row['assist_avg']:.1f}"
                    elif key == 'top_low_kills': val = f"{first_row['kill_avg']:.1f}"
                    
                    text_parts.append("- " + template.format(name=name, val=val))
                    
        outro_msg = random.choice(MONTH_END_HYPE_OUTRO_MESSAGES)
        text_parts.append(f"_{outro_msg}_")
        
        msg = "\n\n".join(text_parts)
        res = messenger.send_message(msg, msg_type="MONTH_END_HYPE")
        if res:
            mark_job_sent("month_end_hype")
    else:
        logger.info(f"Not end of month yet (days left: {days_left}). Skipping hype.")
        mark_job_sent("month_end_hype")

def recover_missed_jobs(timezone):
    """Checks the JSON state file and executes any jobs that were scheduled for today but missed."""
    messenger = get_messenger()
    if not messenger.wait_until_ready():
        logger.error("Messenger not ready, aborting recovery of missed jobs.")
        return
        
    logger.info("Checking for missed cron jobs today...")
    state = get_cron_state()
    sent_jobs = state.get("sent_jobs", [])
    now = datetime.now(timezone)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    jobs_config = [
        ("citation", CRON_CITATION_SCHEDULE, send_daily_citation),
        ("win_check", CRON_WIN_CHECK_SCHEDULE, send_daily_win_check),
        ("morning_motivation", CRON_MORNING_MOTIVATION_SCHEDULE, send_morning_motivation),
        ("monthly_awards", CRON_MONTHLY_AWARDS_SCHEDULE, send_monthly_awards),
        ("month_end_hype", CRON_END_OF_MONTH_HYPE_SCHEDULE, send_month_end_hype)
    ]
    
    for job_id, schedule, func in jobs_config:
        if job_id in sent_jobs:
            continue
            
        try:
            trigger = CronTrigger.from_crontab(schedule, timezone=timezone)
            next_fire = trigger.get_next_fire_time(start_of_today, start_of_today)
            
            # If the job was scheduled to run today, and that time is already past (or now)
            if next_fire and next_fire <= now:
                logger.info(f"Recovering missed job: {job_id}")
                try:
                    func()
                except Exception as e:
                    logger.error(f"Failed to recover job {job_id}: {e}")
        except ValueError as e:
            logger.error(f"Invalid cron format for {job_id} during recovery: {e}")

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

    try:
        trigger_awards = CronTrigger.from_crontab(CRON_MONTHLY_AWARDS_SCHEDULE, timezone=timezone)
        scheduler.add_job(send_monthly_awards, trigger_awards)
        logger.info(f"Monthly awards job scheduled with '{CRON_MONTHLY_AWARDS_SCHEDULE}' in {timezone}")
    except ValueError as e:
        logger.error(f"Invalid cron format: {CRON_MONTHLY_AWARDS_SCHEDULE}. Error: {e}. Monthly awards cron disabled.")
        
    try:
        trigger_hype = CronTrigger.from_crontab(CRON_END_OF_MONTH_HYPE_SCHEDULE, timezone=timezone)
        scheduler.add_job(send_month_end_hype, trigger_hype)
        logger.info(f"Month end hype job scheduled with '{CRON_END_OF_MONTH_HYPE_SCHEDULE}' in {timezone}")
    except ValueError as e:
        logger.error(f"Invalid cron format: {CRON_END_OF_MONTH_HYPE_SCHEDULE}. Error: {e}. Month end hype cron disabled.")

    scheduler.add_job(recover_missed_jobs, args=[timezone])
    
    # Also schedule it to run every hour to retry any failed/missed jobs
    try:
        trigger_recovery = CronTrigger.from_crontab('0 * * * *', timezone=timezone)
        scheduler.add_job(recover_missed_jobs, trigger_recovery, args=[timezone])
        logger.info("Hourly recovery job scheduled.")
    except ValueError as e:
        logger.error(f"Failed to schedule hourly recovery job: {e}")

    scheduler.start()
    logger.info("Cron scheduler started.")
