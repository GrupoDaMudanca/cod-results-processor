import pandas as pd

OBJECTIVE_KEYS = [
    "4K", "8K", "12K", "16K",
    "4KD", "5KD", "6KD", "7KD",
    "5W", "10W", "15W", "20W",
    "25SK", "32SK", "36SK", "40SK"
]

def calculate_objectives(df: pd.DataFrame, valid_clan_names: list[str]) -> list[dict]:
    """
    Calculates the monthly objectives for each clan member.
    Returns a list of dicts with player_name, total_completed, and the objectives dict.
    """
    if df.empty:
        return []

    # Calculate squad kills for each match
    squad_kills_map = df.groupby('match_id')['kills'].sum().to_dict()
    df_with_sk = df.copy()
    df_with_sk['squad_kills'] = df_with_sk['match_id'].map(squad_kills_map)

    # Filter for clan members only for the individual objectives
    # The squad kills themselves included non-clan members because of the step above!
    clan_df = df_with_sk[df_with_sk['player_name'].isin(valid_clan_names)]
    
    if clan_df.empty:
        return []

    # Calculate maxes per player
    max_kills = clan_df.groupby('player_name')['kills'].max()
    max_damage = clan_df.groupby('player_name')['damage'].max()
    matches_played = clan_df.groupby('player_name')['match_id'].nunique()
    max_sk = clan_df.groupby('player_name')['squad_kills'].max()

    results = []

    for player in clan_df['player_name'].unique():
        k = max_kills.get(player, 0)
        d = max_damage.get(player, 0)
        w = matches_played.get(player, 0)
        sk = max_sk.get(player, 0)

        objs = {
            "4K": k >= 4,
            "8K": k >= 8,
            "12K": k >= 12,
            "16K": k >= 16,
            "4KD": d >= 4000,
            "5KD": d >= 5000,
            "6KD": d >= 6000,
            "7KD": d >= 7000,
            "5W": w >= 5,
            "10W": w >= 10,
            "15W": w >= 15,
            "20W": w >= 20,
            "25SK": sk >= 25,
            "32SK": sk >= 32,
            "36SK": sk >= 36,
            "40SK": sk >= 40
        }

        total = sum(objs.values())

        results.append({
            "player_name": player,
            "objectives": objs,
            "total_completed": total
        })

    # Sort by total completed descending
    results.sort(key=lambda x: x['total_completed'], reverse=True)
    return results
