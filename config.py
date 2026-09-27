import os
import time

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_DESIRED_MODEL = os.environ.get('GEMINI_DESIRED_MODEL')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

USE_LOCAL_LLM = os.environ.get('USE_LOCAL_LLM', 'false').lower() == 'true'
LOCAL_LLM_ENDPOINT = os.environ.get('LOCAL_LLM_ENDPOINT', 'http://llama.home.arpa:11434/v1/chat/completions')
LOCAL_LLM_MODEL = os.environ.get('LOCAL_LLM_MODEL', 'qwen2.5:3b')
LOCAL_LLM_TIMEOUT = int(os.environ.get('LOCAL_LLM_TIMEOUT', '5'))
RESULT_FILETYPES = os.environ.get('RESULT_FILETYPES').replace(' ', '').split(',')
RESULT_FILES_PATH = os.environ.get('RESULT_FILES_PATH')
OUTPUT_FILES_PATH = os.environ.get('OUTPUT_FILES_PATH')
TEMP_OUTPUT_FILES_NAME = os.environ.get('TEMP_OUTPUT_FILES_PATH')
LATEST_OUTPUT_FILE_NAME = os.environ.get('LATEST_OUTPUT_FILE_NAME')
NEW_OUTPUT_FILES_PATH = os.environ.get('NEW_OUTPUT_FILES_PATH')
PLAYER_NAMES_FILE_PATH = os.environ.get('PLAYER_NAMES_FILE_PATH')
IGNORE_STATE_FILE_PATH = os.environ.get('IGNORE_STATE_FILE_PATH', '.data/ignore_state.json')
ERASE_STATE_FILE_PATH = os.environ.get('ERASE_STATE_FILE_PATH', '.data/erase_state.json')
BACKFILL_STATE_FILE_PATH = os.environ.get('BACKFILL_STATE_FILE_PATH', '.data/backfill_state.json')
UNRESTRICT_STATE_FILE_PATH = os.environ.get('UNRESTRICT_STATE_FILE_PATH', '.data/unrestrict_state.json')
CRON_STATE_FILE_PATH = os.environ.get('CRON_STATE_FILE_PATH', '.data/cron_state.json')
CITATIONS_FILE_PATH = os.environ.get('CITATIONS_FILE_PATH', '.data/citations.jsonl')
CRON_CITATION_SCHEDULE = os.environ.get('CRON_CITATION_SCHEDULE', '0 12 * * *')
CRON_WIN_CHECK_SCHEDULE = os.environ.get('CRON_WIN_CHECK_SCHEDULE', '0 20 * * *')
CRON_MORNING_MOTIVATION_SCHEDULE = os.environ.get('CRON_MORNING_MOTIVATION_SCHEDULE', '0 9 * * *')
CRON_MONTHLY_AWARDS_SCHEDULE = os.environ.get('CRON_MONTHLY_AWARDS_SCHEDULE', '0 10 1 * *')
CRON_END_OF_MONTH_HYPE_SCHEDULE = os.environ.get('CRON_END_OF_MONTH_HYPE_SCHEDULE', '0 10 * * *')
TZ = os.environ.get('TZ', 'UTC')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

EVOLUTION_API_URL = os.environ.get('EVOLUTION_API_URL', 'http://evolution-api:8080')
EVOLUTION_INSTANCE_NAME = os.environ.get('EVOLUTION_INSTANCE_NAME', 'default')
EVOLUTION_API_KEY = os.environ.get('AUTHENTICATION_API_KEY', '429683C4C977415CAAFCCE10F7D57E11')
WHATSAPP_CHAT_ID = os.environ.get('WHATSAPP_CHAT_ID')
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))

EVOLUTION_SEND_TEXT_ENDPOINT = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
EVOLUTION_SEND_MEDIA_ENDPOINT = f"{EVOLUTION_API_URL}/message/sendMedia/{EVOLUTION_INSTANCE_NAME}"
EVOLUTION_GET_CHAT_ENDPOINT = f"{EVOLUTION_API_URL}/group/findGroupInfos/{EVOLUTION_INSTANCE_NAME}"
EVOLUTION_GET_BASE64_MEDIA_ENDPOINT = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE_NAME}"
EVOLUTION_CONNECT_INSTANCE_ENDPOINT = f"{EVOLUTION_API_URL}/instance/connectionState/{EVOLUTION_INSTANCE_NAME}"

LATEST_OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILES_PATH, LATEST_OUTPUT_FILE_NAME)
TEMP_OUTPUT_FILES_PATH = os.path.join(OUTPUT_FILES_PATH, TEMP_OUTPUT_FILES_NAME)
TEMP_OUTPUT_FILE_PATH = os.path.join(TEMP_OUTPUT_FILES_PATH, f'{str(int(time.time()))}.csv')

# Ensure directories exist
os.makedirs(RESULT_FILES_PATH, exist_ok=True)
os.makedirs(OUTPUT_FILES_PATH, exist_ok=True)
os.makedirs(TEMP_OUTPUT_FILES_PATH, exist_ok=True)
