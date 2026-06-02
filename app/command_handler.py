import random
import re
import logging

logger = logging.getLogger(__name__)

from app.messengers import get_messenger
from app.messages import (
    PROCESSING_MESSAGES, BACKFILL_START_MESSAGES, BACKFILL_END_MESSAGES,
    UNAUTHORIZED_MESSAGES, INVALID_BACKFILL_FORMAT_MESSAGES,
    DASHBOARD_START_MESSAGES, DASHBOARD_END_MESSAGES,
    DASHBOARD_NO_DATA_MESSAGES, DASHBOARD_FUTURE_MONTH_MESSAGES,
    BACKFILL_ALREADY_ACTIVE_MESSAGES, BACKFILL_NOT_ACTIVE_MESSAGES,
    DASHBOARD_INVALID_FORMAT_MESSAGES, DASHBOARD_TOO_MANY_MONTHS_MESSAGES,
    DASHBOARD_INVERTED_DATES_MESSAGES, BACKFILL_UNRESTRICTED_MESSAGES,
    BACKFILL_RESTRICTED_MESSAGES
)
from app.backfill import set_backfill, clear_backfill, get_backfill, set_unrestricted, clear_unrestricted, is_unrestricted

def handle_command(text: str, message_id: str, from_id: str, chat_id: str, is_admin: bool = False):
    messenger = get_messenger()
    
    if text.startswith('/backfill'):
        if text == '/backfill unrestrict':
            if not is_admin:
                messenger.send_message(random.choice(UNAUTHORIZED_MESSAGES), reply_to_message_id=message_id, msg_type="UNAUTHORIZED")
                return
            set_unrestricted()
            messenger.send_message(random.choice(BACKFILL_UNRESTRICTED_MESSAGES), reply_to_message_id=message_id, msg_type="BACKFILL_UNRESTRICTED")
            return
            
        if text == '/backfill restrict':
            if not is_admin:
                messenger.send_message(random.choice(UNAUTHORIZED_MESSAGES), reply_to_message_id=message_id, msg_type="UNAUTHORIZED")
                return
            clear_unrestricted()
            messenger.send_message(random.choice(BACKFILL_RESTRICTED_MESSAGES), reply_to_message_id=message_id, msg_type="BACKFILL_RESTRICTED")
            return

        if not is_admin and not is_unrestricted():
            messenger.send_message(random.choice(UNAUTHORIZED_MESSAGES), reply_to_message_id=message_id, msg_type="UNAUTHORIZED")
            return
            
        if text == '/backfill end':
            if not get_backfill():
                messenger.send_message(random.choice(BACKFILL_NOT_ACTIVE_MESSAGES), reply_to_message_id=message_id, msg_type="BACKFILL_NOT_ACTIVE")
                return
            clear_backfill()
            messenger.send_message(random.choice(BACKFILL_END_MESSAGES), reply_to_message_id=message_id, msg_type="BACKFILL_END")
        else:
            args = text.strip().split()
            if len(args) > 1:
                date_str = args[1]
                match1 = re.match(r'^(\d{4})/(\d{2})$', date_str)
                match2 = re.match(r'^(\d{2})/(\d{4})$', date_str)
                
                if match1:
                    year = match1.group(1)
                    month = match1.group(2)
                elif match2:
                    year = match2.group(2)
                    month = match2.group(1)
                else:
                    messenger.send_message(random.choice(INVALID_BACKFILL_FORMAT_MESSAGES), reply_to_message_id=message_id, msg_type="INVALID_BACKFILL_FORMAT")
                    return
                
                if get_backfill():
                    messenger.send_message(random.choice(BACKFILL_ALREADY_ACTIVE_MESSAGES), reply_to_message_id=message_id, msg_type="BACKFILL_ALREADY_ACTIVE")
                    return
                
                set_backfill(year, month)
                message_text = random.choice(BACKFILL_START_MESSAGES).format(month=month, year=year)
                messenger.send_message(message_text, reply_to_message_id=message_id, msg_type="BACKFILL_START")
            else:
                messenger.send_message(random.choice(INVALID_BACKFILL_FORMAT_MESSAGES), reply_to_message_id=message_id, msg_type="INVALID_BACKFILL_FORMAT")
    
    elif text.startswith(('/dashboard', '/dash')):
        from dashboard import generate_dashboard_image
        from datetime import datetime
        
        args = text.strip().split()
        start_date = None
        end_date = None
        
        def parse_date_arg(date_str):
            match_yyyy = re.match(r'^(\d{4})$', date_str)
            if match_yyyy:
                year = int(match_yyyy.group(1))
                now_dt = datetime.now()
                if year == now_dt.year:
                    return datetime(year, 1, 1), datetime(year, now_dt.month, 1)
                return datetime(year, 1, 1), datetime(year, 12, 1)
                
            match1 = re.match(r'^(\d{4})/(\d{2})$', date_str)
            match2 = re.match(r'^(\d{2})/(\d{4})$', date_str)
            if match1:
                dt = datetime(int(match1.group(1)), int(match1.group(2)), 1)
                return dt, dt
            elif match2:
                dt = datetime(int(match2.group(2)), int(match2.group(1)), 1)
                return dt, dt
            return None, None

        if len(args) == 2:
            s_dt, e_dt = parse_date_arg(args[1])
            if s_dt is None:
                messenger.send_message(random.choice(DASHBOARD_INVALID_FORMAT_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_INVALID_FORMAT")
                return
            start_date = s_dt
            end_date = e_dt
        elif len(args) >= 3:
            if re.match(r'^(\d{4})$', args[1]) or re.match(r'^(\d{4})$', args[2]):
                messenger.send_message(random.choice(DASHBOARD_INVALID_FORMAT_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_INVALID_FORMAT")
                return
                
            s_dt, _ = parse_date_arg(args[1])
            _, e_dt = parse_date_arg(args[2])
            
            if s_dt is None or e_dt is None:
                messenger.send_message(random.choice(DASHBOARD_INVALID_FORMAT_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_INVALID_FORMAT")
                return
            start_date = s_dt
            end_date = e_dt
            
        if start_date and end_date:
            if start_date > end_date:
                messenger.send_message(random.choice(DASHBOARD_INVERTED_DATES_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_INVERTED_DATES")
                return
                
            months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            if months_diff > 11:
                messenger.send_message(random.choice(DASHBOARD_TOO_MANY_MONTHS_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_TOO_MANY_MONTHS")
                return
                
            now_dt = datetime.now()
            if start_date > now_dt or end_date > now_dt:
                messenger.send_message(random.choice(DASHBOARD_FUTURE_MONTH_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_FUTURE_MONTH")
                return
            
            messenger.send_message(random.choice(DASHBOARD_START_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_START")
            dashboard_path = generate_dashboard_image(start_date=start_date, end_date=end_date)
        else:
            messenger.send_message(random.choice(DASHBOARD_START_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_START")
            dashboard_path = generate_dashboard_image()
            
        if dashboard_path:
            messenger.send_photo(dashboard_path, caption=random.choice(DASHBOARD_END_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_REPLY")
        else:
            messenger.send_message(random.choice(DASHBOARD_NO_DATA_MESSAGES), reply_to_message_id=message_id, msg_type="DASHBOARD_NO_DATA")
    
    elif text.startswith('/'):
        # Log unexpected commands if needed
        pass
