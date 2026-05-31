import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from config import LATEST_OUTPUT_FILE_PATH, PLAYER_NAMES_FILE_PATH

def load_data():
    if not os.path.exists(LATEST_OUTPUT_FILE_PATH):
        return pd.DataFrame()
    
    df = pd.read_csv(LATEST_OUTPUT_FILE_PATH)
    
    # Filter only clan members (those with a mapped player_name)
    df = df[df['player_name'].notna() & (df['player_name'] != '')]
    return df

def generate_dashboard_image(output_path='results/dashboard.png'):
    df = load_data()
    if df.empty:
        logger.warning("No data available to generate dashboard.")
        return None

    # Load clan names just to be sure we only include valid ones
    with open(PLAYER_NAMES_FILE_PATH, 'r') as f:
        clan_mapping = json.load(f)
    valid_clan_names = list(clan_mapping.keys())
    df = df[df['player_name'].isin(valid_clan_names)]

    if df.empty:
        logger.warning("No clan data available to generate dashboard.")
        return None

    # Global Stats
    total_plays = df['match_id'].nunique()
    total_kills = int(df['kills'].sum())
    avg_kills = total_kills / total_plays if total_plays > 0 else 0

    # Player Stats
    player_stats = df.groupby('player_name').agg(
        wins=('match_id', 'nunique'),
        kills=('kills', 'sum'),
        damage=('damage', 'sum'),
        assists=('assists', 'sum') if 'assists' in df.columns else ('kills', 'sum') # fallback
    ).reset_index()

    player_stats['kill_avg'] = player_stats['kills'] / player_stats['wins']
    player_stats['damage_avg'] = player_stats['damage'] / player_stats['wins']
    
    # Sort for table
    player_stats = player_stats.sort_values(by='kills', ascending=False)

    # Calculate Highlights
    most_wins_row = player_stats.loc[player_stats['wins'].idxmax()]
    most_wins_str = f"{most_wins_row['player_name']}:{int(most_wins_row['wins'])}"

    tadinho = player_stats.loc[player_stats['kill_avg'].idxmin()]['player_name']

    # Rouba Kill: highest assists/kills ratio
    player_stats['rouba_ratio'] = player_stats['assists'] / player_stats['kills'].clip(lower=1)
    rouba_kill = player_stats.loc[player_stats['rouba_ratio'].idxmax()]['player_name']

    # Gasta Bala: highest damage/kills ratio for those with above average damage
    avg_damage = player_stats['damage'].mean()
    high_dmg_players = player_stats[player_stats['damage'] > avg_damage].copy()
    if high_dmg_players.empty:
        high_dmg_players = player_stats # fallback
    high_dmg_players['dmg_per_kill'] = high_dmg_players['damage'] / high_dmg_players['kills'].clip(lower=1)
    gasta_bala = high_dmg_players.loc[high_dmg_players['dmg_per_kill'].idxmax()]['player_name']

    # ------------------
    # Plotting
    # ------------------
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(8, 12))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')
    ax.axis('off')

    # Title
    current_date = datetime.now()
    month_name = current_date.strftime('%B').capitalize()
    year = current_date.strftime('%Y')
    
    plt.text(0.5, 0.95, "Destaques de Ressurgência", color="white", fontsize=24, fontweight='bold', ha='center', va='center', transform=ax.transAxes)
    plt.text(0.5, 0.91, f"{month_name} / {year}", color="#a0a0b0", fontsize=16, ha='center', va='center', transform=ax.transAxes)

    # Function to draw a card
    def draw_card(x, y, w, h, title, value, title_color="#ffb86c", val_color="white"):
        # Box
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03", 
                             ec="none", fc="#16213e", transform=ax.transAxes)
        ax.add_patch(box)
        # Title
        plt.text(x + w/2, y + h*0.7, title, color=title_color, fontsize=12, fontweight='bold', ha='center', va='center', transform=ax.transAxes)
        # Value
        plt.text(x + w/2, y + h*0.3, value, color=val_color, fontsize=16, fontweight='bold', ha='center', va='center', transform=ax.transAxes)

    # Cards (7 total)
    # Row 1 (3 cards)
    y_r1 = 0.75
    h_c = 0.10
    w_c = 0.25
    x_gap = 0.05
    x_start = (1 - (3*w_c + 2*x_gap)) / 2

    draw_card(x_start, y_r1, w_c, h_c, "Total Plays", str(total_plays))
    draw_card(x_start + w_c + x_gap, y_r1, w_c, h_c, "Total Kills", str(total_kills))
    draw_card(x_start + 2*(w_c + x_gap), y_r1, w_c, h_c, "Average Kills", f"{avg_kills:.1f}")

    # Row 2 (3 cards)
    y_r2 = 0.62
    draw_card(x_start, y_r2, w_c, h_c, "Wins", most_wins_str)
    draw_card(x_start + w_c + x_gap, y_r2, w_c, h_c, "Tadinho", tadinho)
    draw_card(x_start + 2*(w_c + x_gap), y_r2, w_c, h_c, "Rouba Kill", rouba_kill)

    # Row 3 (1 card, center)
    y_r3 = 0.49
    draw_card(x_start, y_r3, w_c, h_c, "Gasta Bala", gasta_bala)

    # ------------------
    # Table
    # ------------------
    # We will draw a custom table using text elements to have full styling control
    y_tbl_start = 0.40
    
    headers = ["Atleta", "Wins", "Kill Avg", "Kills", "Damage Avg", "Damage"]
    x_cols = [0.1, 0.28, 0.42, 0.58, 0.75, 0.90]
    aligns = ['left', 'center', 'center', 'center', 'center', 'right']

    # Header
    for idx, (h_text, x_pos, align) in enumerate(zip(headers, x_cols, aligns)):
        plt.text(x_pos, y_tbl_start, h_text, color="#ffb86c", fontsize=12, fontweight='bold', ha=align, va='center', transform=ax.transAxes)
    
    plt.plot([0.1, 0.9], [y_tbl_start-0.02, y_tbl_start-0.02], color="#a0a0b0", lw=1, transform=ax.transAxes)

    # Rows
    y_row = y_tbl_start - 0.06
    for i, row in player_stats.iterrows():
        # format values
        dmg_str = f"{row['damage']/1000:.1f}k" if row['damage'] >= 1000 else str(int(row['damage']))
        dmg_avg_str = f"{row['damage_avg']:.0f}"
        
        row_vals = [
            str(row['player_name']),
            str(int(row['wins'])),
            f"{row['kill_avg']:.1f}",
            str(int(row['kills'])),
            dmg_avg_str,
            dmg_str
        ]
        
        # Draw background band for alternate rows
        if i % 2 == 0:
            band = FancyBboxPatch((0.08, y_row-0.015), 0.84, 0.03, ec="none", fc="#16213e", transform=ax.transAxes, alpha=0.5)
            ax.add_patch(band)

        for val, x_pos, align in zip(row_vals, x_cols, aligns):
            plt.text(x_pos, y_row, val, color="white", fontsize=11, ha=align, va='center', transform=ax.transAxes)
        
        y_row -= 0.04

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    
    return output_path

if __name__ == '__main__':
    # For local testing
    path = generate_dashboard_image()
    if path:
        print(f"Dashboard generated at {path}")
