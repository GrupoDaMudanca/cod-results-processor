import json
import os
import random
import logging
from datetime import datetime
from config import CITATIONS_FILE_PATH

logger = logging.getLogger(__name__)

def save_citation(text: str) -> bool:
    """Appends a citation to the JSONL file."""
    try:
        os.makedirs(os.path.dirname(CITATIONS_FILE_PATH), exist_ok=True)
        
        entry = {
            "text": text,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(CITATIONS_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
        logger.info(f"Saved citation: {text}")
        return True
    except Exception as e:
        logger.error(f"Failed to save citation: {e}")
        return False

def get_random_citation() -> str:
    """Returns a random citation from the JSONL file, or None if empty."""
    if not os.path.exists(CITATIONS_FILE_PATH):
        return None
        
    try:
        citations = []
        with open(CITATIONS_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        citations.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if not citations:
            return None
            
        return random.choice(citations).get("text")
    except Exception as e:
        logger.error(f"Failed to read citations: {e}")
        return None
