from app.ai_enricher import get_message
"""
Metric: Anchor (High Quantity Redeploys)

Meaning:
Identifies the player who survived the longest during the match, allowing the team to redeploy from the Gulag/Respawn.
This is a positive metric (praise) that rewards the player who acted as the squad's "Anchor".

Calculation:
- Dashboard (Aggregated): Average redeploys per match (`redeploys / matches played`). The player with the HIGHEST average wins.
- Bot (Single Match): Evaluates if the player's redeploy count is statistically high (Z-Score > 1.2) compared to the team's average in the match.
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import HIGH_REDEPLOYS_MESSAGES


def calculate(players: list[dict]) -> list[dict]:
    """Returns the candidates with the highest redeploys sorted from highest to lowest."""
    if not players:
        return []

    eligible_players = [
        r for r in players
        if r.get('is_clan_member', True) and r.get('redeploys', 0) >= 3
    ]

    if not eligible_players:
        return None

    for p in eligible_players:
        wins = p.get('wins', 1)
        p['_eff_redeploys'] = p.get('redeploys', 0) / wins if wins > 0 else 0

    sorted_players = sorted(eligible_players, key=lambda r: r.get('_eff_redeploys', 0), reverse=True)
    return sorted_players


def calculate_outlier(players: list[dict], worst: dict | None) -> tuple[float, float]:
    """Returns the redeploys z_score and kills z_score."""
    if not worst or not players:
        return 0.0, 0.0

    redeploys_list = [r.get('_eff_redeploys', r.get('redeploys', 0) / r.get('wins', 1) if r.get('wins', 1) > 0 else 0) for r in players]
    redeploys_mean = sum(redeploys_list) / len(redeploys_list)

    variance = sum((rd - redeploys_mean) ** 2 for rd in redeploys_list) / len(redeploys_list)
    std_dev = math.sqrt(variance)

    z_score = (worst.get('redeploys', 0) - redeploys_mean) / std_dev if std_dev > 0 else 0

    kills_list = [r.get('kills', 0) for r in players]
    kills_mean = sum(kills_list) / len(kills_list)
    kills_variance = sum((k - kills_mean) ** 2 for k in kills_list) / len(kills_list)
    kills_std_dev = math.sqrt(kills_variance)

    kills_z_score = (worst.get('kills', 0) - kills_mean) / kills_std_dev if kills_std_dev > 0 else 0

    return z_score, kills_z_score


class HighQuantityRedeploys(MetricReply):
    """Detects players with significantly high redeploys compared to the group."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        sorted_players = calculate(report)
        if not sorted_players:
            return MetricResult(score=0, message=None)
            
        worst = sorted_players[0]
        z_score, kills_z_score = calculate_outlier(report, worst)

        if not worst or z_score <= 1.2:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 20))

        if kills_z_score > 0.5:
            return MetricResult(score=0, message=None)

        message = get_message(HIGH_REDEPLOYS_MESSAGES).format(player_name=worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
