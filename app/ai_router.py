import logging
import requests
import json
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant"
]

SYSTEM_PROMPT_TEMPLATE = """You are the internal command router for a Call of Duty statistics bot on Telegram and WhatsApp.
The user spoke to the bot in natural language. Your goal is to map the user's intent to a valid command. Current date: {current_date}

SUPPORTED COMMANDS:
- `/citation` -> requests a random citation/quote.
- `/citation "quote text" - AUTHOR NAME` -> saves a new citation.
- `/dashboard` -> requests the statistics dashboard. (Can receive dates as arguments: `/dashboard YYYY/MM` or `/dashboard YYYY` or a range `/dashboard YYYY/MM YYYY/MM`). If the user asks for "up to today" or similar, the second argument should be the current month/year.
- `/backfill start YYYY/MM` -> starts backfilling old data for a specific month.
- `/backfill end` -> stops the current backfill.

STRICT RULES:
1. You must not converse, you must not greet, you must not explain anything.
2. You must ONLY return a valid JSON with the key "command_text".
3. If you cannot map the intent to any known command, return null in the value.

Examples:
User: "@bot guarda essa citação pra mim: \"jogou muito\" - pedro"
Output: {"command_text": "/citation \"jogou muito\" - pedro"}

User: "@bot me dê uma pérola do clã"
Output: {"command_text": "/citation"}

User: "@bot me mostre as estatísticas"
Output: {"command_text": "/dashboard"}

User: "faz um café pra mim"
Output: {"command_text": null}
"""

def route_message_to_command(text: str) -> str:
    """
    Tries to map a natural language string to an internal command using Groq AI.
    Returns:
        - The mapped command string (e.g. '/citation')
        - "ERROR_API" if all models fail (rate limits, timeouts, etc.)
        - "ERROR_MAPPING" if the model explicitly maps it to null (didn't understand).
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set.")
        return "ERROR_API"
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Clean the text from mention artifacts if possible, though the LLM can handle it.
    cleaned_text = text.strip()
    
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{current_date}", current_date)
    
    for model in MODELS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cleaned_text}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        
        logger.info(f"Trying AI routing with model: {model}")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            
            command_text = result.get("command_text")
            
            if command_text is None:
                logger.info(f"Model {model} returned null (ERROR_MAPPING). Text: {cleaned_text}")
                return "ERROR_MAPPING"
                
            logger.info(f"Model {model} successfully routed to: {command_text}")
            return command_text
            
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.warning(f"Response: {e.response.text}")
            continue
            
    logger.error("All AI models failed to route the message (ERROR_API).")
    return "ERROR_API"
