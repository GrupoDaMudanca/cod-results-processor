from app.ai_enricher import get_message
"""
Metric: High Score

Meaning:
Identifies the player who looted the most and did the most contracts, accumulating a high match score.

Calculation:
A Z-score is used to ensure the player's score was an extreme outlier compared to the rest of the team (Z-score > 1.2).
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages.metrics import HIGH_SCORE_MESSAGES


def calculate(players: list[dict]) -> list[dict]:
    """Returns the players sorted by Score from highest to lowest."""
    if not players:
        return []

    valid_players = [p for p in players if p.get('is_clan_member', True) and 'score' in p]
    sorted_players = sorted(valid_players, key=lambda p: p.get('score', 0), reverse=True)
    return sorted_players


def calculate_outlier(players: list[dict], best: dict | None) -> float:
    """Returns the z-score for the Highest Score."""
    if not best or not players:
        return 0.0

    scores = [p.get('score', 0) for p in players if 'score' in p]
    if not scores:
        return 0.0

    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)

    z_score = (best.get('score', 0) - mean_score) / std_dev if std_dev > 0 else 0
    return z_score


class HighScore(MetricReply):
    """Detects the player who achieved an extremely high score in the match."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        sorted_players = calculate(report)
        if not sorted_players:
            return MetricResult(score=0, message=None)
            
        best = sorted_players[0]
        z_score = calculate_outlier(report, best)

        # Require a higher Z-score (1.2) for score since it's a secondary metric
        if not best or z_score <= 1.2:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 25))
        message = get_message(HIGH_SCORE_MESSAGES).format(player_name=best['player_name'])

        return MetricResult(score=normalized_score, message=message)
