"""
Metric: Kill Stealer

Meaning:
Identifies the player who has many kills but very little damage dealt. In other words, the person who only landed the final shot to steal the elimination their teammate worked hard for.

Calculation:
- General (Dashboard & Bot): Calculates the ratio `Total Damage / Kills`. The player with the LOWEST ratio (least damage required to get a kill) wins this metric.
- Bot (Single Match): Uses the ratio above and calculates a Z-Score to ensure the person is statistically stealing significantly more kills than the team average (Z-Score >= 0.8).
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import KILL_STEALER_MESSAGES


def calculate(players: list[dict]) -> list[dict]:
    """Returns the kill stealers sorted from worst to best."""
    eligible_players = [
        p for p in players 
        if p.get('is_clan_member', True) and p.get('kills', 0) > 0
    ]

    if not eligible_players:
        return []

    # Calculate ratio: damage / kills
    for p in eligible_players:
        p['_dmg_per_kill'] = p.get('damage', 0) / p.get('kills', 1)

    sorted_players = sorted(eligible_players, key=lambda x: x.get('_dmg_per_kill', 0))
    return sorted_players

def calculate_outlier(players: list[dict], best_stealer: dict | None) -> float:
    """Returns the z-score for the given candidate among all players."""
    if not best_stealer:
        return 0.0

    all_ratios = [
        p.get('damage', 0) / p.get('kills', 1) 
        for p in players if p.get('kills', 0) > 0
    ]

    if not all_ratios:
        return 0.0

    eff_mean = sum(all_ratios) / len(all_ratios)
    eff_variance = sum((r - eff_mean) ** 2 for r in all_ratios) / len(all_ratios)
    eff_std_dev = math.sqrt(eff_variance)

    z_score = (eff_mean - best_stealer.get('_dmg_per_kill', 0)) / eff_std_dev if eff_std_dev > 0 else 0
    return z_score


class KillStealer(MetricReply):
    """Detects players with high kills but very low damage."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        sorted_players = calculate(report)
        if not sorted_players:
            return MetricResult(score=0, message=None)
            
        best_stealer = sorted_players[0]
        z_score = calculate_outlier(report, best_stealer)
        
        if not best_stealer or z_score < 0.8:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 25))
        message = random.choice(KILL_STEALER_MESSAGES)(best_stealer['player_name'])

        return MetricResult(score=normalized_score, message=message)
