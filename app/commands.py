import logging
import pandas as pd
from app.helpers import file_valid, get_player_names_map
from config import LATEST_OUTPUT_FILE_PATH

logger = logging.getLogger(__name__)

def reload_missing_player_names() -> int:
    """Read the latest CSV, find missing player_names, and update them using player_names.json. Returns updated count."""
    if file_valid(LATEST_OUTPUT_FILE_PATH):
        return 0
        
    try:
        df = pd.read_csv(LATEST_OUTPUT_FILE_PATH)
        names_dict = get_player_names_map()
        
        updated_players = set()
        updated_rows = 0
        for index, row in df.iterrows():
            if pd.isna(row['player_name']) or str(row['player_name']).strip() in ('', 'None', 'nan'):
                p_id = str(row['player_id']).strip()
                if p_id in names_dict:
                    df.at[index, 'player_name'] = names_dict[p_id]
                    updated_players.add(names_dict[p_id])
                    updated_rows += 1
                    
        if updated_rows > 0:
            df.to_csv(LATEST_OUTPUT_FILE_PATH, index=False)
            
        return len(updated_players)
    except Exception as e:
        logger.error(f"Error in reload_missing_player_names: {e}")
        return 0
