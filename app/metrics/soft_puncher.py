"""
Metric: Soft Puncher

Meaning:
Identifies the player who dealt a lot of damage to enemies but failed to confirm the eliminations, resulting in many assists (or high damage with low kills). 

Calculation:
- General (Dashboard & Bot): Calculates the ratio `Assists / max(Kills, 1)`. The player with the HIGHEST ratio wins the metric.
- Bot (Single Match): Applies a Z-Score to the ratio above to ensure the player was a statistical outlier compared to the rest of the team (Z-Score >= 0.8).
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import SOFT_PUNCHER_MESSAGES


def calculate(players: list[dict]) -> list[dict]:
    """Returns the soft punchers sorted from worst to best."""
    eligible_players = [
        p for p in players 
        if p.get('is_clan_member', True) and p.get('assists', 0) > 0
    ]

    if not eligible_players:
        return []

    # Calculate ratio: assists / max(kills, 1)
    for p in eligible_players:
        p['_soft_ratio'] = p.get('assists', 0) / max(p.get('kills', 0), 1)

    sorted_players = sorted(eligible_players, key=lambda x: x.get('_soft_ratio', 0), reverse=True)
    return sorted_players

def calculate_outlier(players: list[dict], worst: dict | None) -> float:
    """Returns the z-score for the given candidate among all players."""
    if not worst:
        return 0.0

    # Calculate mean and std dev among all players
    all_ratios = [p.get('assists', 0) / max(p.get('kills', 0), 1) for p in players]
    eff_mean = sum(all_ratios) / len(all_ratios) if all_ratios else 0
    eff_variance = sum((r - eff_mean) ** 2 for r in all_ratios) / len(all_ratios) if all_ratios else 0
    eff_std_dev = math.sqrt(eff_variance)

    z_score = (worst.get('_soft_ratio', 0) - eff_mean) / eff_std_dev if eff_std_dev > 0 else 0
    return z_score


class SoftPuncher(MetricReply):
    """Detects players with high assists compared to kills."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        sorted_players = calculate(report)
        if not sorted_players:
            return MetricResult(score=0, message=None)
            
        worst = sorted_players[0]
        z_score = calculate_outlier(report, worst)
        
        if not worst or z_score < 0.8:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 25))
        message = random.choice(SOFT_PUNCHER_MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
