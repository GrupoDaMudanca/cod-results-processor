from app.ai_enricher import get_message
"""
Metric: Match MVP

Meaning:
Identifies the player who had the highest Base Score in a single match.

Calculation:
Base Score = (Kills * 10) + (Assists * 5) + (Redeploys * 5) + (Damage / 100)
A Z-score is used to ensure the MVP truly carried the team (Z-score > 0.8).
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages.metrics import MATCH_MVP_MESSAGES


def calculate_base_score(p: dict) -> float:
    return (p.get('kills', 0) * 10) + (p.get('assists', 0) * 5) + (p.get('redeploys', 0) * 5) + (p.get('damage', 0) / 100.0)


def calculate(players: list[dict]) -> list[dict]:
    """Returns the players sorted by MVP Score from best to worst."""
    if not players:
        return []

    valid_players = [p for p in players if p.get('is_clan_member', True)]
    
    for p in valid_players:
        p['_match_base_score'] = calculate_base_score(p)

    sorted_players = sorted(valid_players, key=lambda p: p.get('_match_base_score', 0), reverse=True)
    return sorted_players


def calculate_outlier(players: list[dict], best: dict | None) -> float:
    """Returns the z-score for the MVP."""
    if not best or not players:
        return 0.0

    scores = [calculate_base_score(p) for p in players]
    if not scores:
        return 0.0

    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)

    z_score = (best.get('_match_base_score', 0) - mean_score) / std_dev if std_dev > 0 else 0
    return z_score


class MatchMVP(MetricReply):
    """Detects the player who carried the match."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        sorted_players = calculate(report)
        if not sorted_players:
            return MetricResult(score=0, message=None)
            
        best = sorted_players[0]
        z_score = calculate_outlier(report, best)

        if not best or z_score <= 0.8:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 25))
        message = get_message(MATCH_MVP_MESSAGES).format(player_name=best['player_name'])

        return MetricResult(score=normalized_score, message=message)
