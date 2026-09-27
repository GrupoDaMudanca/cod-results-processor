from app.ai_enricher import get_message
"""
Metric: Match LVP (Least Valuable Player)

Meaning:
Identifies the player who had the lowest Base Score in a single match.

Calculation:
Base Score = (Kills * 10) + (Assists * 5) + (Redeploys * 5) + (Damage / 100)
A Z-score is used to ensure the player was truly a dead weight compared to the team (Z-score > 0.8).
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages.metrics import MATCH_LVP_MESSAGES
from app.metrics.match_mvp import calculate_base_score


def calculate(players: list[dict]) -> list[dict]:
    """Returns the players sorted by MVP Score from worst to best."""
    if not players:
        return []

    valid_players = [p for p in players if p.get('is_clan_member', True)]
    
    for p in valid_players:
        p['_match_base_score'] = calculate_base_score(p)

    sorted_players = sorted(valid_players, key=lambda p: p.get('_match_base_score', 0))
    return sorted_players


def calculate_outlier(players: list[dict], worst: dict | None) -> float:
    """Returns the z-score for the LVP (positive means they are far below average)."""
    if not worst or not players:
        return 0.0

    scores = [calculate_base_score(p) for p in players]
    if not scores:
        return 0.0

    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)

    # Note that for LVP, we want the Z-score to measure how far BELOW average they are
    z_score = (mean_score - worst.get('_match_base_score', 0)) / std_dev if std_dev > 0 else 0
    return z_score


class MatchLVP(MetricReply):
    """Detects the player who dragged the team down."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        sorted_players = calculate(report)
        if not sorted_players:
            return MetricResult(score=0, message=None)
            
        worst = sorted_players[0]
        z_score = calculate_outlier(report, worst)

        if not worst or z_score <= 0.8:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 25))
        message = get_message(MATCH_LVP_MESSAGES).format(player_name=worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
