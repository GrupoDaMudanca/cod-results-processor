import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

from config import LATEST_OUTPUT_FILE_PATH, PLAYER_NAMES_FILE_PATH, RESULT_FILES_PATH

from app.objectives import calculate_objectives, OBJECTIVE_KEYS
from app.rank_system import calculate_sr_and_rank

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
        # We now filter by exact datetime boundaries, inclusive
        start_bound = pd.to_datetime(start_date).tz_localize(None)
        end_bound = pd.to_datetime(end_date).tz_localize(None)
        df = df[(df['parsed_date'].dt.tz_localize(None) >= start_bound) & 
                (df['parsed_date'].dt.tz_localize(None) <= end_bound)]
                
    if 'ignore_stats' in df.columns:
        df = df[df['ignore_stats'] != True]
    
    return df
    
def get_highlights_for_period(start_date, end_date):
    """Loads data for a period, calculates objectives and SR, and returns highlights."""
    df = load_data(start_date, end_date)
    if df.empty:
        return None
        
    with open(PLAYER_NAMES_FILE_PATH, 'r') as f:
        clan_mapping = json.load(f)
    valid_clan_names = list(clan_mapping.keys())

    months = df['parsed_date'].dt.tz_localize(None).dt.to_period('M').unique() if 'parsed_date' in df.columns else [None]
    player_monthly_sr = {}
    
    for month in months:
        month_df = df[df['parsed_date'].dt.tz_localize(None).dt.to_period('M') == month] if month is not None else df
        if month_df.empty:
            continue
            
        objs_list_month = calculate_objectives(month_df, valid_clan_names)
        obj_dict_month = {p['player_name']: p['total_completed'] for p in objs_list_month}
        wins_month = month_df[month_df['player_name'].isin(valid_clan_names)].groupby('player_name')['match_id'].nunique()
        
        month_stats = {}
        for player in valid_clan_names:
            w = wins_month.get(player, 0)
            o = obj_dict_month.get(player, 0)
            if w > 0 or o > 0:
                sr, rank, mult = calculate_sr_and_rank(w, o)
                month_stats[player] = [sr, rank, mult, w]
                
        # Elect Rei Delas for the month
        cands = [p for p, stats in month_stats.items() if stats[1] == 'Iridescente' and stats[3] >= 30]
        if cands:
            month_player_stats = month_df[month_df['player_name'].isin(cands)].groupby('player_name').agg(
                kills=('kills', 'sum'),
                damage=('damage', 'sum'),
                assists=('assists', 'sum') if 'assists' in month_df.columns else ('kills', 'sum'),
                redeploys=('redeploys', 'sum') if 'redeploys' in month_df.columns else ('kills', 'sum')
            ).reset_index()
            
            best_cand = None
            best_wins = -1
            best_mvp = -1
            
            for _, row in month_player_stats.iterrows():
                p = row['player_name']
                w = month_stats[p][3]
                k = row['kills'] / w if w > 0 else 0
                a = row['assists'] / w if w > 0 else 0
                r = row['redeploys'] / w if w > 0 else 0
                d = row['damage'] / w if w > 0 else 0
                mult = month_stats[p][2]
                mvp = ((k * 10) + (a * 5) + (r * 5) + (d / 100)) * mult
                if w > best_wins or (w == best_wins and mvp > best_mvp):
                    best_cand = p
                    best_wins = w
                    best_mvp = mvp
                    
            if best_cand:
                month_stats[best_cand][1] = 'Rei_Delas'
                
        for player, stats in month_stats.items():
            if player not in player_monthly_sr:
                player_monthly_sr[player] = []
            player_monthly_sr[player].append((stats[0], stats[1], stats[2]))

    objs_list_ui = calculate_objectives(df, valid_clan_names)
    played_players = df[df['player_name'].isin(valid_clan_names)]['player_name'].unique()
    objs_list = [p for p in objs_list_ui if p['player_name'] in played_players]
    objs_list.sort(key=lambda x: x['total_completed'], reverse=True)
    
    total_objs_dict = {p['player_name']: p['total_completed'] for p in objs_list}

    df = df[df['player_name'].isin(valid_clan_names)]
    if df.empty:
        return None
        
    highlights = get_monthly_highlights(df, player_monthly_sr, total_objs_dict)
    return df, highlights, player_monthly_sr, total_objs_dict, months, objs_list
    
def get_monthly_highlights(df, player_monthly_sr, total_objs_dict):
    """Calculates and returns the top players for each category."""
    player_stats = df.groupby('player_name').agg(
        wins=('match_id', 'nunique'),
        kills=('kills', 'sum'),
        damage=('damage', 'sum'),
        assists=('assists', 'sum') if 'assists' in df.columns else ('kills', 'sum'),
        redeploys=('redeploys', 'sum') if 'redeploys' in df.columns else ('kills', 'sum')
    ).reset_index()

    player_stats['objectives'] = player_stats['player_name'].map(lambda x: total_objs_dict.get(x, 0))

    # Calculate basic averages
    player_stats['kill_avg'] = player_stats['kills'] / player_stats['wins']
    player_stats['damage_avg'] = player_stats['damage'] / player_stats['wins']
    player_stats['redeploy_avg'] = player_stats.get('redeploys', player_stats['kills']) / player_stats['wins']
    player_stats['assist_avg'] = player_stats['assists'] / player_stats['wins']
    
    # We now calculate damage per kill strictly (fixing waste_bullet)
    player_stats['dmg_per_kill'] = player_stats['damage'] / player_stats['kills'].replace(0, 1)

    # Score (if not in df, default to 0)
    if 'score' in df.columns:
        score_df = df.groupby('player_name')['score'].sum().reset_index()
        player_stats = player_stats.merge(score_df, on='player_name', how='left')
        player_stats['score'] = player_stats['score'].fillna(0)
    else:
        player_stats['score'] = 0
    player_stats['score_avg'] = player_stats['score'] / player_stats['wins']

    # Apply Multi-month SR and Multiplier
    # The multiplier is based on the Average SR across all active months (or just the period months)
    # The Rank is the PEAK rank achieved in any month
    num_months = df['parsed_date'].dt.tz_localize(None).dt.to_period('M').nunique() if 'parsed_date' in df.columns else 1
    if num_months == 0:
        num_months = 1

    def get_aggregated_sr(player):
        monthly_data = player_monthly_sr.get(player, [])
        if not monthly_data:
            return 500, "🥉 Bronze", 0.5
        
        # Peak rank is the one with the highest SR
        peak_entry = max(monthly_data, key=lambda x: x[0])
        peak_rank = peak_entry[1]
        
        # Average SR across all months in the period
        # If they didn't play in a month, their SR for that month is 500.
        played_months_sr_sum = sum(x[0] for x in monthly_data)
        missed_months = num_months - len(monthly_data)
        
        avg_sr = (played_months_sr_sum + (missed_months * 500)) / num_months
        avg_mult = round(avg_sr / 1000.0, 1)
        
        return avg_sr, peak_rank, avg_mult

    sr_data = player_stats['player_name'].apply(get_aggregated_sr)
    player_stats['sr'] = [x[0] for x in sr_data]
    player_stats['rank'] = [x[1] for x in sr_data]
    player_stats['multiplier'] = [x[2] for x in sr_data]

    # Final Rei Delas Election
    cands_rei = player_stats[player_stats['rank'] == 'Rei_Delas'].copy()
    if not cands_rei.empty:
        cands_rei['rei_count'] = cands_rei['player_name'].apply(lambda p: sum(1 for m in player_monthly_sr.get(p, []) if m[1] == 'Rei_Delas'))
        temp_base = (cands_rei['kill_avg'] * 10) + (cands_rei['assist_avg'] * 5) + (cands_rei['redeploy_avg'] * 5) + (cands_rei['damage_avg'] / 100)
        cands_rei['_temp_mvp'] = temp_base * cands_rei['multiplier']
        
        cands_rei = cands_rei.sort_values(by=['rei_count', 'wins', '_temp_mvp'], ascending=[False, False, False])
        true_rei = cands_rei.iloc[0]['player_name']
        
        # Demote the others back to Iridescente
        losers = cands_rei[cands_rei['player_name'] != true_rei]['player_name']
        if not losers.empty:
            player_stats.loc[player_stats['player_name'].isin(losers), 'rank'] = 'Iridescente'

    # Cap non-Rei-Delas Iridescentes
    mask_iri_cap = (player_stats['rank'] == 'Iridescente') & (player_stats['sr'] > 2099)
    player_stats.loc[mask_iri_cap, 'sr'] = 2099
    player_stats.loc[mask_iri_cap, 'multiplier'] = 2.1

    # Calculate Base Performance Score and MVP
    player_stats['base_score'] = (player_stats['kill_avg'] * 10) + (player_stats['assist_avg'] * 5) + (player_stats['redeploy_avg'] * 5) + (player_stats['damage_avg'] / 100)
    player_stats['mvp_score'] = player_stats['base_score'] * player_stats['multiplier']

    # Asymmetrical Rule: Positive metrics multiplied, Negative metrics pure (no multiplier)
    player_stats['adj_kill_avg'] = player_stats['kill_avg'] * player_stats['multiplier']
    player_stats['adj_redeploy_avg'] = player_stats['redeploy_avg'] * player_stats['multiplier']

    player_stats = player_stats.sort_values(by='mvp_score', ascending=False)

    return {
        'player_stats': player_stats,
        'top_mvp': player_stats.nlargest(3, 'mvp_score'),
        'top_sr': player_stats.nlargest(3, 'sr'),
        'top_wins': player_stats.nlargest(3, 'wins'),
        'top_avg_kills': player_stats.nlargest(3, 'adj_kill_avg'),
        'top_high_redeploys': player_stats.nlargest(3, 'adj_redeploy_avg'),
        'top_soft_puncher': player_stats.nlargest(3, 'assist_avg'),
        'top_score': player_stats.nlargest(3, 'score_avg'),
        
        'top_lvp': player_stats.nsmallest(3, 'mvp_score'),
        'top_waste_bullet': player_stats.nlargest(3, 'dmg_per_kill'),
        'top_kill_stealer': player_stats.nsmallest(3, 'dmg_per_kill'),
        'top_low_redeploys': player_stats.nsmallest(3, 'redeploy_avg'),
        'top_low_kills': player_stats.nsmallest(3, 'kill_avg')
    }
def generate_dashboard_image(output_path=None, start_date=None, end_date=None):
    if output_path is None:
        output_path = os.path.join(RESULT_FILES_PATH, 'dashboard.png')
        
    if not start_date or not end_date:
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        end_date = start_date

    res = get_highlights_for_period(start_date, end_date)
    if not res:
        logger.warning("No data available to generate dashboard.")
        return None
        
    df, highlights, player_monthly_sr, total_objs_dict, months, objs_list = res
    player_stats = highlights['player_stats']
    num_months = len([m for m in months if m is not None]) or 1

    total_plays = df['match_id'].nunique()
    total_kills = int(df['kills'].sum())

    # Formatter helpers
    def format_val(df_subset, key, fmt_str="{:.1f}"):
        return [(r['player_name'], fmt_str.format(r[key])) for _, r in df_subset.iterrows()]

    mvp_list = format_val(highlights['top_mvp'], 'mvp_score')
    sr_list = [(r['player_name'], str(int(r['sr']))) for _, r in highlights['top_sr'].iterrows()]
    wins_list = [(r['player_name'], str(int(r['wins']))) for _, r in highlights['top_wins'].iterrows()]
    avg_kills_list = format_val(highlights['top_avg_kills'], 'adj_kill_avg')
    high_redeploys_list = format_val(highlights['top_high_redeploys'], 'adj_redeploy_avg')
    soft_puncher_list = format_val(highlights['top_soft_puncher'], 'assist_avg')
    score_list = format_val(highlights['top_score'], 'score_avg', "{:.0f}")

    lvp_list = format_val(highlights['top_lvp'], 'mvp_score')
    waste_bullet_list = format_val(highlights['top_waste_bullet'], 'dmg_per_kill', "{:.0f}")
    kill_stealer_list = format_val(highlights['top_kill_stealer'], 'dmg_per_kill', "{:.0f}")
    low_redeploys_list = format_val(highlights['top_low_redeploys'], 'redeploy_avg')
    low_kills_list = format_val(highlights['top_low_kills'], 'kill_avg')

    avg_kills = total_kills / total_plays if total_plays > 0 else 0


    # Objectives were already calculated above using the full df

    # ------------------
    # Dynamic Layout Calculation
    # ------------------
    num_players_tbl = len(player_stats)
    num_players_obj = len(objs_list)
    
    # Define heights in "inches"
    H_obj = 1.5 + (num_players_obj * 0.35)
    H_tbl = 1.0 + (num_players_tbl * 0.35)
    
    # We now have 3 rows of highlights instead of 2. Make H_top larger.
    H_top = 6.5
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
    plt.rcParams['font.family'] = ['DejaVu Sans']
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
    
    import calendar
    s_full_month = start_date.day == 1
    e_full_month = end_date.day == calendar.monthrange(end_date.year, end_date.month)[1]
    
    def format_date_str(d, is_start):
        if is_start and d.day == 1:
            return f"{PT_MONTHS[d.month][:3]}/{d.year}"
        if not is_start and d.day == calendar.monthrange(d.year, d.month)[1]:
            return f"{PT_MONTHS[d.month][:3]}/{d.year}"
        return f"{d.day:02d}/{d.month:02d}/{d.year}"

    if start_date.year == end_date.year and start_date.month == 1 and end_date.month == 12 and s_full_month and e_full_month:
        title_text = f"Ano de {start_date.year}"
    elif start_date.year == end_date.year and start_date.month == end_date.month:
        if s_full_month and e_full_month:
            title_text = f"{PT_MONTHS[start_date.month]} / {start_date.year}"
        elif start_date.day == end_date.day:
            title_text = f"{start_date.day:02d} de {PT_MONTHS[start_date.month]} / {start_date.year}"
        else:
            title_text = f"{format_date_str(start_date, True)} a {format_date_str(end_date, False)}"
    else:
        title_text = f"{format_date_str(start_date, True)} a {format_date_str(end_date, False)}"
    
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
    hl_bottom_inch = 6.3  # Increased for 3 rows
    hl_box = FancyBboxPatch((0.03, y_pct(hl_bottom_inch)), 0.94, (hl_bottom_inch - hl_top_inch) / H_total, 
                         boxstyle="round,pad=0.02,rounding_size=0.03", mutation_aspect=W_total/H_total,
                         ec="none", fc="#16213e", transform=ax.transAxes)
    ax.add_patch(hl_box)
    
    plt.text(0.05, y_pct(hl_top_inch + 0.3), "Ressurgence Highlights", color="#e94560", fontsize=16, fontweight='bold', ha='left', va='center', transform=ax.transAxes)

    # We will use 4 columns, 3 rows
    x_cols_hl = [0.05, 0.28, 0.51, 0.74]
    y_hl_r1 = hl_top_inch + 0.8
    y_hl_r2 = hl_top_inch + 2.3
    y_hl_r3 = hl_top_inch + 3.8

    # Prestige Row 1
    draw_highlight_col(x_cols_hl[0], y_hl_r1, "MVP", mvp_list)
    draw_highlight_col(x_cols_hl[1], y_hl_r1, "O General (SR)", sr_list)
    draw_highlight_col(x_cols_hl[2], y_hl_r1, "Vencedor Nato", wins_list)
    draw_highlight_col(x_cols_hl[3], y_hl_r1, "O Exterminador", avg_kills_list)

    # Prestige Row 2
    draw_highlight_col(x_cols_hl[0], y_hl_r2, "Highlander", high_redeploys_list)
    draw_highlight_col(x_cols_hl[1], y_hl_r2, "Atira Fofo", soft_puncher_list)
    draw_highlight_col(x_cols_hl[2], y_hl_r2, "Zé Lootinho", score_list)
    
    # Mockery Row 3 (starts at column 3 of Row 2)
    draw_highlight_col(x_cols_hl[3], y_hl_r2, "LVP", lvp_list)
    
    draw_highlight_col(x_cols_hl[0], y_hl_r3, "Gasta Bala", waste_bullet_list)
    draw_highlight_col(x_cols_hl[1], y_hl_r3, "Rouba Kill", kill_stealer_list)
    draw_highlight_col(x_cols_hl[2], y_hl_r3, "Neymar", low_redeploys_list)
    draw_highlight_col(x_cols_hl[3], y_hl_r3, "Tadinho", low_kills_list)


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
    
    rank_col_label = "Rank" if num_months <= 1 else "Melhor Rank"
    headers = ["Atleta", rank_col_label, "SR", "Avg Mult", "MVP", "Wins", "Kill Avg", "Kills", "Assists", "Redepl", "Dmg"]
    # 11 columns — squeeze a bit to fit SR between Rank and Mult
    x_cols = [0.05, 0.17, 0.275, 0.34, 0.41, 0.48, 0.545, 0.625, 0.715, 0.82, 0.95]
    aligns = ['left', 'center', 'center', 'center', 'center', 'center', 'center', 'center', 'center', 'center', 'right']

    # Header
    for idx, (h_text, x_pos, align) in enumerate(zip(headers, x_cols, aligns)):
        plt.text(x_pos, y_pct(y_tbl_start_inch), h_text, color="#ffb86c", fontsize=11, fontweight='bold', ha=align, va='center', transform=ax.transAxes)
    
    plt.plot([0.05, 0.95], [y_pct(y_tbl_start_inch + 0.25), y_pct(y_tbl_start_inch + 0.25)], color="#a0a0b0", lw=1, transform=ax.transAxes)

    # Rows
    y_row_inch = y_tbl_start_inch + 0.65
    for i, row in player_stats.iterrows():
        dmg_str = f"{row['damage']/1000:.1f}k" if row['damage'] >= 1000 else str(int(row['damage']))
        
        row_vals = [
            str(row['player_name']),
            str(row['rank']),
            f"{row['sr']:.0f}",
            f"x{row['multiplier']:.1f}",
            f"{row['mvp_score']:.1f}",
            str(int(row['wins'])),
            f"{row['kill_avg']:.1f}",
            str(int(row['kills'])),
            str(int(row['assists'])),
            str(int(row.get('redeploys', 0))),
            dmg_str
        ]
        
        if i % 2 == 0:
            import matplotlib.patches as patches
            band = patches.Rectangle((0.06, y_pct(y_row_inch + 0.15)), 0.88, 0.3 / H_total, ec="none", fc="#16213e", transform=ax.transAxes, alpha=0.5)
            ax.add_patch(band)
            
        for idx, (val, x_pos, align) in enumerate(zip(row_vals, x_cols, aligns)):
            if idx == 1:
                import matplotlib.image as mpimg
                from matplotlib.offsetbox import OffsetImage, AnnotationBbox
                if row['rank']:
                    rank_en_map = {
                        "Bronze": "Bronze", "Prata": "Silver", "Ouro": "Gold",
                        "Platina": "Platinum", "Diamante": "Diamond", 
                        "Carmesim": "Crimson", "Iridescente": "Iridescent",
                        "Rei_Delas": "king"
                    }
                    pt_rank = row['rank'].split()[0] if " " in row['rank'] else row['rank']
                    rank_base = rank_en_map.get(pt_rank, "Bronze")
                    if pt_rank in ["Bronze", "Prata", "Ouro", "Platina", "Diamante", "Carmesim"]:
                        sub_rank = row['rank'].split()[1] if len(row['rank'].split()) > 1 else "I"
                        badge_filename = f"{rank_base}_{sub_rank}.png"
                    else:
                        badge_filename = f"{rank_base}.png"
                    badge_path = os.path.join('assets', 'badges', badge_filename)
                
                try:
                    img = mpimg.imread(badge_path)
                    imagebox = OffsetImage(img, zoom=0.16)  # smaller zoom to avoid row overlap
                    imagebox.image.axes = ax
                    
                    ab = AnnotationBbox(imagebox, (x_pos, y_pct(y_row_inch)),
                                        frameon=False,
                                        xycoords='axes fraction',
                                        box_alignment=(0.5, 0.5))
                    ax.add_artist(ab)
                except Exception as e:
                    print(f"Error loading {badge_filename}: {e}")
                    plt.text(x_pos, y_pct(y_row_inch), val, color="white", fontsize=11, ha=align, va='center', transform=ax.transAxes)
            else:
                plt.text(x_pos, y_pct(y_row_inch), val, color="white", fontsize=11, ha=align, va='center', transform=ax.transAxes)
            
        y_row_inch += 0.35

    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor())
    plt.close()
    
    return output_path

if __name__ == '__main__':
    # For local testing - August 2026
    path = generate_dashboard_image(start_date=datetime(2026, 8, 1), end_date=datetime(2026, 8, 31))
    if path:
        print(f"Dashboard generated at {path}")
