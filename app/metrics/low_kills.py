"""
Metric: Noob (Low Quantity Kills)

Meaning:
Identifies the player who eliminated the fewest enemies in the match or month. This is the classic mock for someone who couldn't contribute much to the squad's eliminations.

Calculation:
- Dashboard (Aggregated): Average kills per match (`kills / matches played`). The player with the LOWEST average wins.
- Bot (Single Match): Evaluates if the player had a kill count significantly below the team's average (Z-Score <= -1.0). It also includes an automatic trigger for maximum mockery (score 200) if the player finishes with 0 kills in the match.
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import LOW_KILLS_MESSAGES, ZERO_KILLS_MESSAGES


def calculate(players: list[dict]) -> list[dict]:
    """Returns the low kills candidates sorted from worst to best."""
    if not players:
        return []

    for p in players:
        wins = p.get('wins', 1)
        p['_eff_kills'] = p.get('kills', 0) / wins if wins > 0 else 0

    eligible_players = [
        r for r in players
        if r.get('is_clan_member', True)
    ]

    if not eligible_players:
        return []

    sorted_players = sorted(eligible_players, key=lambda r: r.get('_eff_kills', 0))
    return sorted_players

def calculate_outlier(players: list[dict], worst: dict | None) -> tuple[float, bool, float]:
    """Returns z-score, is_zero flag, and kills_mean."""
    if not worst or not players:
        return 0.0, False, 0.0

    is_zero = worst.get('kills', -1) == 0

    kills_list = [r.get('_eff_kills', r.get('kills', 0) / r.get('wins', 1) if r.get('wins', 1) > 0 else 0) for r in players]
    kills_mean = sum(kills_list) / len(kills_list)

    variance = sum((k - kills_mean) ** 2 for k in kills_list) / len(kills_list)
    std_dev = math.sqrt(variance)

    z_score = (worst.get('_eff_kills', 0) - kills_mean) / std_dev if std_dev > 0 else 0
    return z_score, is_zero, kills_mean


class LowQtdKills(MetricReply):
    """Detects players with significantly low kills compared to the group average."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        sorted_players = calculate(report)
        if not sorted_players:
            return MetricResult(score=0, message=None)
            
        worst = sorted_players[0]
        z_score, is_zero, kills_mean = calculate_outlier(report, worst)

        if not worst:
            return MetricResult(score=0, message=None)

        if is_zero:
            message = random.choice(ZERO_KILLS_MESSAGES)(worst['player_name'])
            return MetricResult(score=200.0, message=message)

        # z-score threshold: considered low if 1 std dev below mean
        if z_score >= -1.0:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, abs(z_score) * 25))

        # Must have at least 2 kills fewer than the average to avoid marginal cases
        if kills_mean - worst.get('kills', 0) < 2:
            return MetricResult(score=0, message=None)

        message = random.choice(LOW_KILLS_MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
