import time
import os
import shutil
import logging

from config import RESULT_FILES_PATH, TEMP_OUTPUT_FILES_PATH, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from telegram_handler import poll_and_download, confirm_updates
from match_processor import process_all
from consolidate import consolidate_data
from dashboard import generate_dashboard_image
from app.telegram import send_photo
from app.messages import FALLBACK_MESSAGES


def cleanup():
    """Clean up the results and processed/temp folders after a successful cycle."""
    for folder in [RESULT_FILES_PATH, TEMP_OUTPUT_FILES_PATH]:
        full_path = os.path.join(os.getcwd(), folder)
        if os.path.exists(full_path):
            for filename in os.listdir(full_path):
                file_path = os.path.join(full_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f'Failed to delete {file_path}. Reason: {e}')
        else:
            os.makedirs(full_path)

def run_daemon():
    logger.info("Starting Call of Duty results processor bot...")
    
    # Certificar de que as pastas existam ao iniciar
    for folder in [RESULT_FILES_PATH, TEMP_OUTPUT_FILES_PATH]:
        full_path = os.path.join(os.getcwd(), folder)
        os.makedirs(full_path, exist_ok=True)
        
    while True:
        try:
            # Poll with timeout for long-polling
            last_update = poll_and_download(timeout=30)
            
            if last_update:
                logger.info(f"Downloaded images up to offset {last_update}. Starting processing...")
                
                # Confirm to telegram immediately so we don't process them again if we crash
                logger.info("Confirming messages to Telegram...")
                confirm_updates(last_update)
                
                # Process the downloaded files
                processed_any, msg_id, funny_msg = process_all()
                
                if processed_any:
                    logger.info("Processing complete. Consolidating data...")
                    # Consolidate results into latest.csv
                    consolidate_data()
                    
                    logger.info("Generating and sending dashboard...")
                    dashboard_path = generate_dashboard_image()
                    if dashboard_path:
                        if funny_msg:
                            caption = funny_msg
                        else:
                            import random
                            caption = random.choice(FALLBACK_MESSAGES)
                            
                        send_photo(dashboard_path, caption=caption, reply_to_message_id=msg_id)
                    
                # Clean up local temp files
                cleanup()
                
                logger.info("Cycle completed successfully. Waiting for new messages...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(5)  # Pause um pouco antes de tentar novamente para não espamar logs


if __name__ == '__main__':
    run_daemon()
