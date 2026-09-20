import threading
import logging
from flask import Flask, request, jsonify
from config import FLASK_PORT, WHATSAPP_CHAT_ID

logger = logging.getLogger(__name__)

class WhatsAppWebhookServer:
    def __init__(self, queue: list):
        self.queue = queue
        self.app = Flask(__name__)
        self.app.add_url_rule('/webhook', view_func=self.webhook, methods=['POST'])
        
    def webhook(self):
        data = request.json
        logger.debug(f"RAW WEBHOOK RECEIVED: {data}")
        if not data:
            return jsonify({"status": "ignored"}), 200

        event_type = data.get('event')
        
        if event_type == 'messages.upsert':
            messages = data.get('data', {})
            # In v2, Evolution often sends as a simple dict or list
            if not isinstance(messages, list):
                messages = [messages]
                
            for message in messages:
                if message.get('fromMe', False) or message.get('key', {}).get('fromMe', False):
                    continue
                    
                chat_id = message.get('remoteJid') or message.get('key', {}).get('remoteJid')
                if not chat_id:
                    continue
                    
                is_private = not chat_id.endswith('@g.us')
                
                if WHATSAPP_CHAT_ID and not is_private:
                    if chat_id != WHATSAPP_CHAT_ID:
                        continue

                self.queue.append(message)
                msg_id = message.get('key', {}).get('id') or message.get('messageId')
                logger.info(f"Received Evolution message added to queue: {msg_id}")

        return jsonify({"status": "ok"}), 200

    def start(self):
        logger.info(f"Starting Flask webhook server on port {FLASK_PORT}")
        import logging as fl_logging
        log = fl_logging.getLogger('werkzeug')
        log.setLevel(fl_logging.ERROR)
        self.app.run(host='0.0.0.0', port=FLASK_PORT, threaded=True)

    def start_in_background(self):
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        return thread
