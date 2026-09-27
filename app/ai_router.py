import logging
import requests
import json
from config import GROQ_API_KEY, USE_LOCAL_LLM, LOCAL_LLM_ENDPOINT, LOCAL_LLM_MODEL, LOCAL_LLM_TIMEOUT

logger = logging.getLogger(__name__)

MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "groq/compound",
    "openai/gpt-oss-20b"
]

SYSTEM_PROMPT_TEMPLATE = """You are an intent classifier for a Call of Duty statistics bot on WhatsApp.
Your ONLY function is to classify the user's intent into one of the allowed categories and extract any mentioned parameters (names, dates, keywords). You MUST output a valid JSON object. Current date: {current_date}

CATEGORIES (intent):
- citation: Request a random quote.
- searchcitation: Search for a quote using specific keywords.
- save_citation: Save a quote explicitly formatted as 'SOBRENOME, Nome'.
- dashboard: See statistics dashboard (can have dates).
- backfill: Read old match data.
- backfill_end: Stop reading old data.
- reload: Update clan names/nicks.
- erase: Delete or erase a match (e.g. "apagar", "deletar").
- ignore: Ignore or cancel stats for a player (e.g. "ignora fulano", "cancela os stats do tucano").
- ranks: Explain ranking system, SR, or MVP.
- none: Unrelated message or unrecognized command.

YOU MUST RETURN A VALID JSON OBJECT WITH EXACTLY THESE TWO KEYS:
1. "intent": Must be one of the exact categories above.
2. "parameters": If the user specified a target (a name to ignore, keywords to search, dates to filter), extract them here. Otherwise, return an empty string.
   - For 'searchcitation', extract keywords.
   - For 'dashboard' or 'backfill', format dates as DD/MM/YYYY or YYYY/MM. If a date range is requested, you MUST return BOTH dates separated by a space (e.g. '01/01/2026 31/01/2026'). Use the CHEAT SHEET below for relative dates.
   - For 'ignore', extract the player's name.

Example Output:
{"intent": "ignore", "parameters": "tucano"}
{"intent": "dashboard", "parameters": "15/10/2026"}
{"intent": "erase", "parameters": ""}
"""

def route_message_to_command(text: str) -> str:
    """
    Maps a natural language string to an internal command using Groq AI with a fallback to Local LLM.
    Returns:
        - The mapped command string (e.g. '/ignore tucano')
        - "ERROR_API" if all models fail
        - "ERROR_MAPPING" if intent is 'none'
    """
    cleaned_text = text.strip()
    from datetime import datetime, timedelta
    today = datetime.now()
    ontem = (today - timedelta(days=1)).strftime("%d/%m/%Y")
    semana_passada = (today - timedelta(days=7)).strftime("%d/%m/%Y")
    semana_retrasada = (today - timedelta(days=14)).strftime("%d/%m/%Y")
    mes_passado = (today.replace(day=1) - timedelta(days=1)).strftime("%m/%Y")
    
    cheat_sheet = f"\nDATE CHEAT SHEET:\n- hoje / today: {today.strftime('%d/%m/%Y')}\n- ontem / yesterday: {ontem}\n- semana passada / last week: {semana_passada}\n- semana retrasada: {semana_retrasada}\n- mes passado / last month: {mes_passado}\n"
    
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{current_date}", today.strftime("%d/%m/%Y")) + cheat_sheet
    
    result = None
    success = False

    # 1. Try Local LLM
    if USE_LOCAL_LLM:
        logger.info(f"Trying Local LLM at {LOCAL_LLM_ENDPOINT} with model {LOCAL_LLM_MODEL}")
        
        # Determine if endpoint is Ollama native or OpenAI-compatible
        is_openai_compat = "/v1/chat/completions" in LOCAL_LLM_ENDPOINT
        
        if is_openai_compat:
            payload = {
                "model": LOCAL_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": cleaned_text}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
                "stream": True
            }
        else:
            # Native Ollama API
            payload = {
                "model": LOCAL_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": cleaned_text}
                ],
                "format": "json",
                "stream": True,
                "options": {"temperature": 0.0},
                "keep_alive": "2h"
            }
            
        try:
            # timeout=(connect_timeout, read_timeout)
            response = requests.post(LOCAL_LLM_ENDPOINT, json=payload, timeout=(3.0, LOCAL_LLM_TIMEOUT), stream=True)
            response.raise_for_status()
            
            full_content = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if is_openai_compat:
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk["choices"][0]["delta"]
                                if "content" in delta and delta["content"]:
                                    full_content += delta["content"]
                            except json.JSONDecodeError:
                                continue
                    else:
                        try:
                            chunk = json.loads(decoded_line)
                            if "message" in chunk and "content" in chunk["message"]:
                                full_content += chunk["message"]["content"]
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
            
            result = json.loads(full_content)
            success = True
        except Exception as e:
            logger.error(f"Local LLM failed: {e}")

    # 2. Try Groq API Fallback
    if not success and GROQ_API_KEY:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
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
            logger.info(f"Trying Groq AI fallback routing with model: {model}")
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                result = json.loads(content)
                success = True
                break
            except Exception as e:
                logger.warning(f"Groq Model {model} failed: {e}")
                continue
    elif not success:
        logger.warning("GROQ_API_KEY is not set. Skipping Groq API fallback.")

    # 3. Process Result
    if not success or not result:
        logger.error("All AI models failed to route the message (ERROR_API).")
        return "ERROR_API"

    intent = result.get("intent", "none").lower()
    params = result.get("parameters", "").strip()
    
    if intent == "none" or not intent:
        logger.info(f"Model returned none intent. Text: {cleaned_text}")
        return "ERROR_MAPPING"
        
    # Python-based Command Construction
    command_final = ""
    if intent == "citation":
        command_final = "/citation"
    elif intent == "searchcitation":
        command_final = f"/searchcitation {params}"
    elif intent == "save_citation":
        command_final = f"/citation {params}"
    elif intent == "dashboard":
        command_final = f"/dashboard {params}"
    elif intent == "backfill":
        command_final = f"/backfill {params}"
    elif intent == "backfill_end":
        command_final = "/backfill end"
    elif intent == "reload":
        command_final = "/reload"
    elif intent == "erase":
        command_final = "/erase"
    elif intent == "ignore":
        command_final = f"/ignore {params}"
    elif intent == "ranks":
        command_final = "/ranks"
    else:
        return "ERROR_MAPPING"
        
    command_final = command_final.strip()
    logger.info(f"Successfully routed intent '{intent}' to command: {command_final}")
    return command_final

