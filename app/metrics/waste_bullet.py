"""
Metric: Bullet Hog (Waste Bullet)

Meaning:
Identifies the player who deals high damage (above average) but gets very few kills. Unlike Soft Puncher (which uses assists), this metric focuses purely on raw damage that did not convert into eliminations.

Calculation:
- General (Dashboard & Bot): First filters for players whose damage was ABOVE average. Among them, calculates the ratio `Damage / max(Kills, 1)`. The player with the HIGHEST damage per kill ratio wins.
- Bot (Single Match): In addition to the above-average damage filter, it requires the player's Kills to be BELOW the team's average. A Z-Score is applied to the Damage/Kill ratio to ensure relevance (Z-Score > 0.8).
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import WASTE_BULLET_MESSAGES


def calculate(players: list[dict]) -> list[dict]:
    """Returns the bullet wasters sorted from worst to best."""
    if not players:
        return []

    damage_mean = sum(r.get('damage', 0) for r in players) / len(players)

    # Simple logic: High damage, highest damage per kill. No check for kills_mean.
    high_damage_players = [
        r for r in players 
        if r.get('damage', 0) > damage_mean and r.get('is_clan_member', True)
    ]
    if not high_damage_players:
        return []

    for r in high_damage_players:
        kills = r.get('kills', 0)
        kills = kills if kills > 0 else 1
        r['_damage_per_kill'] = r.get('damage', 0) / kills

    sorted_players = sorted(high_damage_players, key=lambda p: p.get('_damage_per_kill', 0), reverse=True)
    return sorted_players


def calculate_outlier(players: list[dict], worst: dict | None) -> float:
    """Returns the z-score for the given candidate among high damage players."""
    if not worst or not players:
        return 0.0

    kills_mean = sum(r.get('kills', 0) for r in players) / len(players)
    damage_mean = sum(r.get('damage', 0) for r in players) / len(players)

    # The telegram bot requires kills to be below average to consider it a waste of bullets
    if worst.get('kills', 0) >= kills_mean:
        return 0.0

    high_damage_players = [r for r in players if r.get('damage', 0) > damage_mean]

    player_efficiencies = []
    for r in high_damage_players:
        kills = r.get('kills', 0)
        kills = kills if kills > 0 else 1
        player_efficiencies.append(r.get('damage', 0) / kills)

    eff_mean = sum(player_efficiencies) / len(player_efficiencies)
    eff_variance = sum((p - eff_mean) ** 2 for p in player_efficiencies) / len(player_efficiencies)
    eff_std_dev = math.sqrt(eff_variance)

    z_score = (worst.get('_damage_per_kill', 0) - eff_mean) / eff_std_dev if eff_std_dev > 0 else 0
    return z_score


class WasteBullet(MetricReply):
    """Detects players with high damage but poor kill conversion (wasting bullets)."""

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
        message = random.choice(WASTE_BULLET_MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
