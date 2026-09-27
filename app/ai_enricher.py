import logging
import requests
import json
import random
import re
from config import USE_LOCAL_LLM, LOCAL_LLM_ENDPOINT, LOCAL_LLM_MODEL, LOCAL_LLM_TIMEOUT

logger = logging.getLogger(__name__)

def get_message(message_list: list, context: str = "") -> str:
    """
    Tries to generate a dynamic message using the local LLM, based on the provided list of examples.
    Falls back to a random choice from the list if it fails or times out.
    """
    if not message_list:
        return ""
        
    fallback_message = random.choice(message_list)
        
    if not USE_LOCAL_LLM:
        logger.info(f"[STATIC FALLBACK] ♻️ Mensagem estática (LLM Desativado): {fallback_message}")
        return fallback_message
        
    try:
        # Select 3-5 random messages as examples
        num_examples = min(5, len(message_list))
        examples = random.sample(message_list, num_examples)
        
        examples_text = "\n".join([f"- {msg}" for msg in examples])
        
        system_prompt = (
            "Você é o bot do WhatsApp de um clã de Call of Duty. "
            "Sua personalidade é extremamente ácida, irônica, tóxica (na brincadeira) e impaciente.\n\n"
            "Aqui estão alguns exemplos de mensagens que você costuma mandar nessa situação:\n"
            f"{examples_text}\n\n"
            "Sua tarefa: Gere UMA (1) nova mensagem seguindo a exata mesma vibe e tom irônico dos exemplos, mas com texto diferente. "
            "Seja criativo e soe natural para o WhatsApp. "
            "REGRA CRÍTICA: Se as mensagens de exemplo contiverem palavras entre chaves (como {player_name}, {count}, {days}, etc), VOCÊ DEVE incluir EXATAMENTE as mesmas chaves na sua nova mensagem, pois o sistema usará isso para injetar variáveis. Não altere nem omita essas chaves. "
            "IMPORTANTE: Retorne APENAS o texto da mensagem final, sem aspas, sem explicações, sem introduções."
        )
        
        if context:
            system_prompt += f"\nContexto extra para a mensagem: {context}"
            
        payload = {
            "model": LOCAL_LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Gere a mensagem agora."}
            ],
            "temperature": 0.8,
            "stream": True
        }
        
        logger.info(f"Enriquecendo mensagem com LLM local ({LOCAL_LLM_MODEL})...")
        
        is_openai_compat = "/v1/chat/completions" in LOCAL_LLM_ENDPOINT
        if not is_openai_compat:
            payload["format"] = "json" # Note: for enrichment we don't necessarily want JSON, we want text.
            payload.pop("format", None)
            
        response = requests.post(LOCAL_LLM_ENDPOINT, json=payload, stream=True, timeout=(3.0, 10.0))
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
                        
        enriched_text = full_content.strip()
        if enriched_text:
            if enriched_text.startswith('"') and enriched_text.endswith('"'):
                enriched_text = enriched_text[1:-1]
                
            # Safey check: ensure LLM didn't hallucinate placeholders not in the fallback
            fallback_placeholders = set(re.findall(r'\{([A-Za-z0-9_]+)\}', fallback_message))
            enriched_placeholders = set(re.findall(r'\{([A-Za-z0-9_]+)\}', enriched_text))
            
            if not enriched_placeholders.issubset(fallback_placeholders):
                logger.warning(f"LLM gerou placeholders invalidos {enriched_placeholders}. Fallback ativado.")
                logger.info(f"[STATIC FALLBACK] ♻️ Mensagem estática: {fallback_message}")
                return fallback_message
                
            logger.info(f"[AI ENRICHED] ✨ Mensagem gerada: {enriched_text}")
            return enriched_text
            
    except Exception as e:
        logger.warning(f"Falha ao enriquecer mensagem com LLM local (timeout ou erro): {e}. Usando fallback.")
        logger.info(f"[STATIC FALLBACK] ♻️ Mensagem estática: {fallback_message}")
        
    return fallback_message
