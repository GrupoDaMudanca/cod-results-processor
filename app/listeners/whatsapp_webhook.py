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

        event_type = data.get('dataType')
        message_data = data.get('data', {})

        if event_type == 'message':
            message = message_data.get('message', message_data)

            if message.get('fromMe', False):
                return jsonify({"status": "ignored"}), 200

            if WHATSAPP_CHAT_ID:
                if message.get('from') != WHATSAPP_CHAT_ID and message.get('to') != WHATSAPP_CHAT_ID:
                    return jsonify({"status": "ignored"}), 200

            self.queue.append(message)
            logger.info(f"Received WhatsApp message added to queue: {message.get('id', {}).get('id')}")

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
