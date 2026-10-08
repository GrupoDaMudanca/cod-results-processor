from app.ai_enricher import get_message
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
    DASHBOARD_INVERTED_DATES_MESSAGES
)
from app.backfill import set_backfill, clear_backfill, get_backfill, set_unrestricted, clear_unrestricted, is_unrestricted

def handle_command(text: str, reply_to: dict, from_id: str, chat_id: str, is_admin: bool = False):
    messenger = get_messenger()
    
    if text.startswith('/ignore'):
        if not is_admin and not is_unrestricted():
            messenger.send_message(get_message(UNAUTHORIZED_MESSAGES), reply_to_message=reply_to, msg_type="UNAUTHORIZED")
            return
            
        args = text.strip().split(maxsplit=1)
        if len(args) < 2:
            from app.messages.ignore import IGNORE_MISSING_ARGUMENT_MESSAGES
            messenger.send_message(get_message(IGNORE_MISSING_ARGUMENT_MESSAGES), reply_to_message=reply_to, msg_type="IGNORE_MISSING_ARGUMENT")
            return
            
        player_name = args[1].strip()
        from app.helpers import get_player_names_map
        valid_keys = set(get_player_names_map().values())
        
        # We need the keys of the JSON, which are the values in get_player_names_map (the canonical names)
        # Wait, get_player_names_map returns { "Alias": "Key" }. So values() are the keys in JSON.
        
        # Check case-insensitive match against valid keys
        matched_key = next((k for k in valid_keys if k.lower() == player_name.lower()), None)
        
        if not matched_key:
            from app.messages.ignore import IGNORE_NOT_FOUND_MESSAGES
            messenger.send_message(get_message(IGNORE_NOT_FOUND_MESSAGES).format(player_name=player_name), reply_to_message=reply_to, msg_type="IGNORE_NOT_FOUND")
            return
            
        from app.state_ignore import set_ignore_player
        from app.messages.ignore import IGNORE_ACTIVATED_MESSAGES
        set_ignore_player(matched_key)
        messenger.send_message(get_message(IGNORE_ACTIVATED_MESSAGES).format(player_name=matched_key), reply_to_message=reply_to, msg_type="IGNORE_ACTIVATED")
        return

    if text == '/unrestrict':
        if not is_admin and not is_unrestricted():
            messenger.send_message(get_message(UNAUTHORIZED_MESSAGES), reply_to_message=reply_to, msg_type="UNAUTHORIZED")
            return
        from app.messages.unrestrict import UNRESTRICTED_MESSAGES
        set_unrestricted()
        messenger.send_message(get_message(UNRESTRICTED_MESSAGES), reply_to_message=reply_to, msg_type="UNRESTRICTED")
        return
        
    if text == '/restrict':
        if not is_admin and not is_unrestricted():
            messenger.send_message(get_message(UNAUTHORIZED_MESSAGES), reply_to_message=reply_to, msg_type="UNAUTHORIZED")
            return
        from app.messages.unrestrict import RESTRICTED_MESSAGES
        clear_unrestricted()
        messenger.send_message(get_message(RESTRICTED_MESSAGES), reply_to_message=reply_to, msg_type="RESTRICTED")
        return

    if text.startswith('/backfill'):
        if not is_admin and not is_unrestricted():
            messenger.send_message(get_message(UNAUTHORIZED_MESSAGES), reply_to_message=reply_to, msg_type="UNAUTHORIZED")
            return
            
        if text == '/backfill end':
            if not get_backfill():
                messenger.send_message(get_message(BACKFILL_NOT_ACTIVE_MESSAGES), reply_to_message=reply_to, msg_type="BACKFILL_NOT_ACTIVE")
                return
            clear_backfill()
            messenger.send_message(get_message(BACKFILL_END_MESSAGES), reply_to_message=reply_to, msg_type="BACKFILL_END")
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
                    messenger.send_message(get_message(INVALID_BACKFILL_FORMAT_MESSAGES), reply_to_message=reply_to, msg_type="INVALID_BACKFILL_FORMAT")
                    return
                
                if get_backfill():
                    messenger.send_message(get_message(BACKFILL_ALREADY_ACTIVE_MESSAGES), reply_to_message=reply_to, msg_type="BACKFILL_ALREADY_ACTIVE")
                    return
                
                set_backfill(year, month)
                message_text = get_message(BACKFILL_START_MESSAGES).format(month=month, year=year)
                messenger.send_message(message_text, reply_to_message=reply_to, msg_type="BACKFILL_START")
            else:
                messenger.send_message(get_message(INVALID_BACKFILL_FORMAT_MESSAGES), reply_to_message=reply_to, msg_type="INVALID_BACKFILL_FORMAT")
    
    elif text.startswith(('/dashboard', '/dash')):
        from dashboard import generate_dashboard_image
        from datetime import datetime
        import dateparser
        import calendar
        
        start_date = None
        end_date = None
        
        # Remove the command prefix
        param_str = re.sub(r'^/dash(board)?\s*', '', text.strip())
        
        def parse_date_arg(date_str):
            date_str = date_str.strip()
            match_yyyy = re.match(r'^(\d{4})$', date_str)
            if match_yyyy:
                year = int(match_yyyy.group(1))
                now_dt = datetime.now()
                if year == now_dt.year:
                    return datetime(year, 1, 1), datetime(year, now_dt.month, calendar.monthrange(year, now_dt.month)[1], 23, 59, 59)
                return datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59)
                
            match1 = re.match(r'^(\d{4})/(\d{2})$', date_str)
            match2 = re.match(r'^(\d{2})/(\d{4})$', date_str)
            if match1 or match2:
                if match1:
                    year, month = int(match1.group(1)), int(match1.group(2))
                else:
                    year, month = int(match2.group(2)), int(match2.group(1))
                last_day = calendar.monthrange(year, month)[1]
                return datetime(year, month, 1), datetime(year, month, last_day, 23, 59, 59)
                
            match_dd_mm_yyyy = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', date_str)
            if match_dd_mm_yyyy:
                day, month, year = int(match_dd_mm_yyyy.group(1)), int(match_dd_mm_yyyy.group(2)), int(match_dd_mm_yyyy.group(3))
                return datetime(year, month, day), datetime(year, month, day, 23, 59, 59)
                
            # Fallback to dateparser for NLP
            parsed = dateparser.parse(date_str, languages=['pt'], settings={'PREFER_DATES_FROM': 'past'})
            if parsed:
                return datetime(parsed.year, parsed.month, parsed.day), datetime(parsed.year, parsed.month, parsed.day, 23, 59, 59)
                
            return None, None

        if param_str:
            # Check if it's a range separated by " a ", " ate ", " até ", " e ", " - "
            range_split = re.split(r'\s+(?:a|até|ate|e|-|until|to)\s+', param_str, maxsplit=1)
            
            # If the user literally just typed two dates separated by a space (the AI used to do this)
            if len(range_split) == 1 and " " in param_str:
                # If there are exactly two tokens that look like dates
                tokens = param_str.split()
                if len(tokens) == 2:
                    range_split = tokens

            if len(range_split) == 2:
                s_dt, _ = parse_date_arg(range_split[0])
                _, e_dt = parse_date_arg(range_split[1])
                if s_dt is None or e_dt is None:
                    messenger.send_message(get_message(DASHBOARD_INVALID_FORMAT_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_INVALID_FORMAT")
                    return
                start_date = s_dt
                end_date = e_dt
            else:
                s_dt, e_dt = parse_date_arg(param_str)
                if s_dt is None:
                    messenger.send_message(get_message(DASHBOARD_INVALID_FORMAT_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_INVALID_FORMAT")
                    return
                start_date = s_dt
                end_date = e_dt
        elif len(args) >= 3:
            if re.match(r'^(\d{4})$', args[1]) or re.match(r'^(\d{4})$', args[2]):
                messenger.send_message(get_message(DASHBOARD_INVALID_FORMAT_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_INVALID_FORMAT")
                return
                
            s_dt, _ = parse_date_arg(args[1])
            _, e_dt = parse_date_arg(args[2])
            
            if s_dt is None or e_dt is None:
                messenger.send_message(get_message(DASHBOARD_INVALID_FORMAT_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_INVALID_FORMAT")
                return
            start_date = s_dt
            end_date = e_dt
            
        if start_date and end_date:
            if start_date > end_date:
                messenger.send_message(get_message(DASHBOARD_INVERTED_DATES_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_INVERTED_DATES")
                return
                
            months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            if months_diff > 11:
                messenger.send_message(get_message(DASHBOARD_TOO_MANY_MONTHS_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_TOO_MANY_MONTHS")
                return
                
            now_dt = datetime.now()
            if start_date.date() > now_dt.date():
                messenger.send_message(get_message(DASHBOARD_FUTURE_MONTH_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_FUTURE_MONTH")
                return
                
            if end_date > now_dt:
                end_date = now_dt
            
            messenger.send_message(get_message(DASHBOARD_START_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_START")
            dashboard_path = generate_dashboard_image(start_date=start_date, end_date=end_date)
        else:
            messenger.send_message(get_message(DASHBOARD_START_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_START")
            dashboard_path = generate_dashboard_image()
            
        if dashboard_path:
            messenger.send_photo(dashboard_path, caption=get_message(DASHBOARD_END_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_REPLY")
        else:
            messenger.send_message(get_message(DASHBOARD_NO_DATA_MESSAGES), reply_to_message=reply_to, msg_type="DASHBOARD_NO_DATA")
    
    elif text.startswith('/searchcitation'):
        from app.citations import search_citations
        from app.messages.citations import CITATION_SEARCH_EMPTY_MESSAGES
        
        args = text.split(maxsplit=1)
        if len(args) > 1:
            keywords = args[1].strip().split()
            citation = search_citations(keywords)
            if citation:
                messenger.send_message(f"📖 *Pérola:*\n\n{citation}", reply_to_message=reply_to, msg_type="CITATION_SEARCH_SUCCESS")
            else:
                messenger.send_message(get_message(CITATION_SEARCH_EMPTY_MESSAGES), reply_to_message=reply_to, msg_type="CITATION_SEARCH_EMPTY")
        else:
            messenger.send_message(get_message(CITATION_SEARCH_EMPTY_MESSAGES), reply_to_message=reply_to, msg_type="CITATION_SEARCH_EMPTY")

    elif text.startswith(('/citation')):
        from app.citations import save_citation, get_random_citation
        from app.messages import CITATION_EMPTY_MESSAGES, CITATION_SAVED_MESSAGES, ERROR_UNEXPECTED_MESSAGES
        
        args = text.split(maxsplit=1)
        if len(args) > 1:
            citation_text = args[1].strip()
            success = save_citation(citation_text)
            if success:
                messenger.send_message(get_message(CITATION_SAVED_MESSAGES), reply_to_message=reply_to, msg_type="CITATION_SAVED")
            else:
                messenger.send_message(get_message(ERROR_UNEXPECTED_MESSAGES), reply_to_message=reply_to, msg_type="ERROR_UNEXPECTED")
        else:
            citation = get_random_citation()
            if citation:
                messenger.send_message(f"📖 *Pérola:*\n\n{citation}", reply_to_message=reply_to, msg_type="CITATION_RANDOM")
            else:
                messenger.send_message(get_message(CITATION_EMPTY_MESSAGES), reply_to_message=reply_to, msg_type="CITATION_EMPTY")

    elif text.startswith('/reload'):
        from app.commands import reload_missing_player_names
        from app.messages import RELOAD_START_MESSAGES, RELOAD_SUCCESS_MESSAGES, RELOAD_NO_CHANGES_MESSAGES
        
        messenger.send_message(get_message(RELOAD_START_MESSAGES), reply_to_message=reply_to, msg_type="RELOAD_START")
        
        updated = reload_missing_player_names()
        if updated > 0:
            msg = get_message(RELOAD_SUCCESS_MESSAGES).replace('{count}', str(updated))
            messenger.send_message(msg, reply_to_message=reply_to, msg_type="RELOAD_SUCCESS")
        else:
            messenger.send_message(get_message(RELOAD_NO_CHANGES_MESSAGES), reply_to_message=reply_to, msg_type="RELOAD_NO_CHANGES")

    elif text.startswith('/erase'):
        from app.state_erase import get_erase, set_erase, clear_erase
        from app.messages.erase import ERASE_ACTIVE_MESSAGES, ERASE_INACTIVE_MESSAGES
        
        if not is_admin and not is_unrestricted():
            messenger.send_message(get_message(UNAUTHORIZED_MESSAGES), reply_to_message=reply_to, msg_type="UNAUTHORIZED")
            return

        if get_erase():
            messenger.send_message(get_message(ERASE_ACTIVE_MESSAGES), reply_to_message=reply_to, msg_type="ERASE_ACTIVE")
        else:
            set_erase()
            messenger.send_message(get_message(ERASE_ACTIVE_MESSAGES), reply_to_message=reply_to, msg_type="ERASE_ACTIVE")

    elif text.startswith('/ranks'):
        from app.messages.ranks import RANKS_INFO_MESSAGE
        messenger.send_message(RANKS_INFO_MESSAGE, reply_to_message=reply_to, msg_type="RANKS_INFO")

    elif text.startswith('/'):
        # Log unexpected commands if needed
        pass

