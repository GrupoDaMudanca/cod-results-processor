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

from config import LATEST_OUTPUT_FILE_PATH, PLAYER_NAMES_FILE_PATH, RESULT_FILES_PATH

from app.objectives import calculate_objectives, OBJECTIVE_KEYS

from pandas.errors import EmptyDataError

def load_data(start_date=None, end_date=None):
    if not os.path.exists(LATEST_OUTPUT_FILE_PATH) or os.stat(LATEST_OUTPUT_FILE_PATH).st_size == 0:
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(LATEST_OUTPUT_FILE_PATH)
    except EmptyDataError:
        return pd.DataFrame()
    
    if not start_date or not end_date:
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        end_date = start_date
    
    if 'date' in df.columns:
        df['parsed_date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
        start_period = pd.to_datetime(start_date).to_period('M')
        end_period = pd.to_datetime(end_date).to_period('M')
        df = df[(df['parsed_date'].dt.to_period('M') >= start_period) & 
                (df['parsed_date'].dt.to_period('M') <= end_period)]
    
    return df

def generate_dashboard_image(output_path=None, start_date=None, end_date=None):
    if output_path is None:
        output_path = os.path.join(RESULT_FILES_PATH, 'dashboard.png')
        
    if not start_date or not end_date:
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        end_date = start_date

    df = load_data(start_date, end_date)
    if df.empty:
        logger.warning("No data available to generate dashboard.")
        return None

    # Load clan names just to be sure we only include valid ones
    with open(PLAYER_NAMES_FILE_PATH, 'r') as f:
        clan_mapping = json.load(f)
    valid_clan_names = list(clan_mapping.keys())
    
    # Pass the full df (including non-clan members) to objectives for accurate squad kills
    objs_list = calculate_objectives(df, valid_clan_names)

    # Filter to only clan members for the rest of the dashboard
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
        assists=('assists', 'sum') if 'assists' in df.columns else ('kills', 'sum'), # fallback
        redeploys=('redeploys', 'sum') if 'redeploys' in df.columns else ('kills', 'sum') # fallback
    ).reset_index()

    player_stats['kill_avg'] = player_stats['kills'] / player_stats['wins']
    player_stats['damage_avg'] = player_stats['damage'] / player_stats['wins']
    
    # Sort for table
    player_stats = player_stats.sort_values(by='kills', ascending=False)

    player_stats['redeploy_avg'] = player_stats.get('redeploys', player_stats['kills']) / player_stats['wins']
    player_stats['assist_avg'] = player_stats['assists'] / player_stats['wins']
    player_stats['dmg_per_kill'] = player_stats['damage'] / player_stats['kills'].replace(0, 1)

    # Calculate Highlights using pure simple averages
    top_kills = player_stats.nlargest(3, 'kills')
    total_kills_list = [(r['player_name'], str(int(r['kills']))) for _, r in top_kills.iterrows()]

    top_avg_kills = player_stats.nlargest(3, 'kill_avg')
    avg_kills_list = [(r['player_name'], f"{r['kill_avg']:.1f}") for _, r in top_avg_kills.iterrows()]

    top_wins = player_stats.nlargest(3, 'wins')
    wins_list = [(r['player_name'], str(int(r['wins']))) for _, r in top_wins.iterrows()]

    top_high_redeploys = player_stats.nlargest(3, 'redeploy_avg')
    high_redeploys_list = [(r['player_name'], f"{r['redeploy_avg']:.1f}") for _, r in top_high_redeploys.iterrows()]

    top_waste_bullet = player_stats.nlargest(3, 'damage_avg')
    waste_bullet_list = [(r['player_name'], f"{r['damage_avg']:.0f}") for _, r in top_waste_bullet.iterrows()]

    top_kill_stealer = player_stats.nsmallest(3, 'dmg_per_kill')
    kill_stealer_list = [(r['player_name'], f"{r['dmg_per_kill']:.0f}") for _, r in top_kill_stealer.iterrows()]

    top_low_redeploys = player_stats.nsmallest(3, 'redeploy_avg')
    low_redeploys_list = [(r['player_name'], f"{r['redeploy_avg']:.1f}") for _, r in top_low_redeploys.iterrows()]

    top_soft_puncher = player_stats.nlargest(3, 'assist_avg')
    soft_puncher_list = [(r['player_name'], f"{r['assist_avg']:.1f}") for _, r in top_soft_puncher.iterrows()]

    top_low_kills = player_stats.nsmallest(3, 'kill_avg')
    low_kills_list = [(r['player_name'], f"{r['kill_avg']:.1f}") for _, r in top_low_kills.iterrows()]

    # Objectives were already calculated above using the full df

    # ------------------
    # Dynamic Layout Calculation
    # ------------------
    num_players = len(player_stats)
    
    # Define heights in "inches"
    H_top = 5.0
    H_obj = 1.5 + (num_players * 0.35)
    H_tbl = 1.0 + (num_players * 0.35)
    H_margin = 0.5
    
    H_total = H_top + H_obj + H_tbl + H_margin
    
    # Dynamically adjust width to keep a pleasant aspect ratio
    # If it's short, make it narrower so it doesn't look stretched horizontally.
    # If it's tall, make it wider up to a limit.
    W_total = max(14.0, min(18.0, H_total * 1.3))
    
    def y_pct(inches_from_top):
        return 1.0 - (inches_from_top / H_total)

    # ------------------
    # Plotting
    # ------------------
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(W_total, H_total))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')
    ax.axis('off')

    # Title
    PT_MONTHS = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    if start_date.year == end_date.year and start_date.month == end_date.month:
        title_text = f"{PT_MONTHS[start_date.month]} / {start_date.year}"
    elif start_date.year == end_date.year and start_date.month == 1 and end_date.month == 12:
        title_text = f"Ano de {start_date.year}"
    else:
        title_text = f"{PT_MONTHS[start_date.month]}/{start_date.year} a {PT_MONTHS[end_date.month]}/{end_date.year}"
    
    plt.text(0.5, y_pct(0.3), "Destaques de Ressurgência", color="white", fontsize=28, fontweight='bold', ha='center', va='center', transform=ax.transAxes)
    plt.text(0.5, y_pct(0.8), title_text, color="#a0a0b0", fontsize=18, ha='center', va='center', transform=ax.transAxes)

    # ------------------
    # Section 1: Highlights
    # ------------------
    def draw_highlight_col(x, y_inch, title, items):
        plt.text(x, y_pct(y_inch), title, color="#ffb86c", fontsize=14, fontweight='bold', ha='left', va='center', transform=ax.transAxes)
        for i in range(3):
            item_y_inch = y_inch + 0.35 + (i * 0.35)
            if i < len(items):
                name, val = items[i]
            else:
                name, val = "-", "-"
            plt.text(x, y_pct(item_y_inch), name, color="white", fontsize=12, ha='left', va='center', transform=ax.transAxes)
            plt.text(x + 0.12, y_pct(item_y_inch), val, color="#a0a0b0", fontsize=12, ha='right', va='center', transform=ax.transAxes)
        
        # Draw a subtle vertical separator line
        plt.plot([x + 0.15, x + 0.15], [y_pct(y_inch - 0.2), y_pct(y_inch + 1.2)], color="#33334d", lw=1, transform=ax.transAxes)

    # Background Box for Highlights
    hl_top_inch = 1.3
    hl_bottom_inch = 4.8
    hl_box = FancyBboxPatch((0.03, y_pct(hl_bottom_inch)), 0.94, (hl_bottom_inch - hl_top_inch) / H_total, 
                         boxstyle="round,pad=0.02,rounding_size=0.03", mutation_aspect=W_total/H_total,
                         ec="none", fc="#16213e", transform=ax.transAxes)
    ax.add_patch(hl_box)
    
    plt.text(0.05, y_pct(hl_top_inch + 0.3), "Ressurgence Highlights", color="#e94560", fontsize=16, fontweight='bold', ha='left', va='center', transform=ax.transAxes)

    x_cols_hl = [0.05, 0.24, 0.43, 0.62, 0.81]
    y_hl_r1 = hl_top_inch + 0.8
    y_hl_r2 = hl_top_inch + 2.3

    draw_highlight_col(x_cols_hl[0], y_hl_r1, "Total Kills", total_kills_list)
    draw_highlight_col(x_cols_hl[1], y_hl_r1, "Avg Kills", avg_kills_list)
    draw_highlight_col(x_cols_hl[2], y_hl_r1, "Wins", wins_list)
    draw_highlight_col(x_cols_hl[3], y_hl_r1, "Rato de Esgoto", high_redeploys_list)
    draw_highlight_col(x_cols_hl[4], y_hl_r1, "Gasta Bala", waste_bullet_list)

    draw_highlight_col(x_cols_hl[0], y_hl_r2, "Rouba Kill", kill_stealer_list)
    draw_highlight_col(x_cols_hl[1], y_hl_r2, "Neymar", low_redeploys_list)
    draw_highlight_col(x_cols_hl[2], y_hl_r2, "Atira Fofo", soft_puncher_list)
    draw_highlight_col(x_cols_hl[3], y_hl_r2, "Tadinho", low_kills_list)


    # ------------------
    # Section 2: Objectives
    # ------------------
    obj_top_inch = H_top + 0.2
    obj_bottom_inch = obj_top_inch + H_obj
    
    obj_box = FancyBboxPatch((0.03, y_pct(obj_bottom_inch)), 0.94, H_obj / H_total, 
                         boxstyle="round,pad=0.02,rounding_size=0.03", mutation_aspect=W_total/H_total,
                         ec="none", fc="#16213e", transform=ax.transAxes)
    ax.add_patch(obj_box)

    plt.text(0.05, y_pct(obj_top_inch + 0.4), "Objectives", color="#e94560", fontsize=16, fontweight='bold', ha='left', va='center', transform=ax.transAxes)

    y_obj_headers = obj_top_inch + 1.0
    x_obj_keys = [0.2 + i * (0.7 / len(OBJECTIVE_KEYS)) for i in range(len(OBJECTIVE_KEYS))]
    x_obj_total = 0.93

    plt.text(0.05, y_pct(y_obj_headers), "Player", color="#ffb86c", fontsize=12, fontweight='bold', ha='left', va='center', transform=ax.transAxes)
    for i, key in enumerate(OBJECTIVE_KEYS):
        plt.text(x_obj_keys[i], y_pct(y_obj_headers), key, color="#ffb86c", fontsize=10, fontweight='bold', ha='center', va='center', transform=ax.transAxes)
    plt.text(x_obj_total, y_pct(y_obj_headers), "Objetivos", color="#ffb86c", fontsize=12, fontweight='bold', ha='center', va='center', transform=ax.transAxes)

    plt.plot([0.05, 0.95], [y_pct(y_obj_headers + 0.25), y_pct(y_obj_headers + 0.25)], color="#33334d", lw=1, transform=ax.transAxes)

    y_obj_row = y_obj_headers + 0.6
    for p_obj in objs_list:
        plt.text(0.05, y_pct(y_obj_row), p_obj['player_name'], color="white", fontsize=11, ha='left', va='center', transform=ax.transAxes)
        for i, key in enumerate(OBJECTIVE_KEYS):
            achieved = p_obj['objectives'].get(key, False)
            color = "#00ff00" if achieved else "#ff0000"
            circle = matplotlib.patches.Circle((x_obj_keys[i], y_pct(y_obj_row)), radius=0.005, color=color, transform=ax.transAxes)
            ax.add_patch(circle)
        plt.text(x_obj_total, y_pct(y_obj_row), str(p_obj['total_completed']), color="white", fontsize=11, ha='center', va='center', transform=ax.transAxes)
        y_obj_row += 0.35


    # ------------------
    # Section 3: Table
    # ------------------
    y_tbl_start_inch = obj_bottom_inch + 0.8
    
    headers = ["Atleta", "Wins", "Kill Avg", "Kills", "Assists", "Redeploys", "Damage Avg", "Damage"]
    x_cols = [0.05, 0.18, 0.30, 0.42, 0.54, 0.66, 0.80, 0.95]
    aligns = ['left', 'center', 'center', 'center', 'center', 'center', 'center', 'right']

    # Header
    for idx, (h_text, x_pos, align) in enumerate(zip(headers, x_cols, aligns)):
        plt.text(x_pos, y_pct(y_tbl_start_inch), h_text, color="#ffb86c", fontsize=12, fontweight='bold', ha=align, va='center', transform=ax.transAxes)
    
    plt.plot([0.05, 0.95], [y_pct(y_tbl_start_inch + 0.25), y_pct(y_tbl_start_inch + 0.25)], color="#a0a0b0", lw=1, transform=ax.transAxes)

    # Rows
    y_row_inch = y_tbl_start_inch + 0.65
    for i, row in player_stats.iterrows():
        dmg_str = f"{row['damage']/1000:.1f}k" if row['damage'] >= 1000 else str(int(row['damage']))
        dmg_avg_str = f"{row['damage_avg']:.0f}"
        
        row_vals = [
            str(row['player_name']),
            str(int(row['wins'])),
            f"{row['kill_avg']:.1f}",
            str(int(row['kills'])),
            str(int(row['assists'])),
            str(int(row.get('redeploys', 0))),
            dmg_avg_str,
            dmg_str
        ]
        
        if i % 2 == 0:
            import matplotlib.patches as patches
            band = patches.Rectangle((0.06, y_pct(y_row_inch + 0.15)), 0.88, 0.3 / H_total, ec="none", fc="#16213e", transform=ax.transAxes, alpha=0.5)
            ax.add_patch(band)
            
        for idx, (val, x_pos, align) in enumerate(zip(row_vals, x_cols, aligns)):
            plt.text(x_pos, y_pct(y_row_inch), val, color="white", fontsize=11, ha=align, va='center', transform=ax.transAxes)
            
        y_row_inch += 0.35

    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor())
    plt.close()
    
    return output_path

if __name__ == '__main__':
    # For local testing
    path = generate_dashboard_image(target_year=2026, target_month=5)
    if path:
        print(f"Dashboard generated at {path}")
