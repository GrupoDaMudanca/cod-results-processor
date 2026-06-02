"""
Metric: Parachutist (Low Quantity Redeploys)

Meaning:
Identifies the player who died the most and needed to redeploy back into the game. Since the game only records a redeploy for the player who survived to buy others back, the one with the FEWEST "redeploys" on the scoreboard is actually the one who died the most (spent the whole game parachuting).

Calculation:
- Dashboard (Aggregated): Average redeploys per match (`redeploys / matches played`). The player with the LOWEST average wins.
- Bot (Single Match): Evaluates if the player had a statistically lower redeploy count than the team's average. It also ignores the player if they had a high number of kills (Kills Z-Score > 0.5), forgiving those who "die a lot but kill a lot".
"""
import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import LOW_REDEPLOYS_MESSAGES


def calculate(players: list[dict]) -> list[dict]:
    """Returns the candidates with the lowest redeploys sorted from worst to best."""
    if not players:
        return []

    # Calculate mean first to avoid picking absolute 0s if they are bugs, 
    # but for redeploys, lowest is actually the one who died most.
    eligible_players = [
        r for r in players
        if r.get('is_clan_member', True)
    ]

    for p in eligible_players:
        wins = p.get('wins', 1)
        p['_eff_redeploys'] = p.get('redeploys', 0) / wins if wins > 0 else 0

    sorted_players = sorted(eligible_players, key=lambda r: r.get('_eff_redeploys', 0))
    return sorted_players


def calculate_outlier(players: list[dict], worst: dict | None) -> tuple[float, float]:
    """Returns the redeploys z_score and kills z_score."""
    if not worst or not players:
        return 0.0, 0.0

    redeploys_list = [r.get('_eff_redeploys', r.get('redeploys', 0) / r.get('wins', 1) if r.get('wins', 1) > 0 else 0) for r in players]
    redeploys_mean = sum(redeploys_list) / len(redeploys_list)

    variance = sum((rd - redeploys_mean) ** 2 for rd in redeploys_list) / len(redeploys_list)
    std_dev = math.sqrt(variance)

    # Note: we want the z_score to be positive when redeploys are LOW, so we subtract worst from mean
    z_score = (redeploys_mean - worst.get('redeploys', 0)) / std_dev if std_dev > 0 else 0

    kills_list = [r.get('kills', 0) for r in players]
    kills_mean = sum(kills_list) / len(kills_list)
    kills_variance = sum((k - kills_mean) ** 2 for k in kills_list) / len(kills_list)
    kills_std_dev = math.sqrt(kills_variance)

    kills_z_score = (worst.get('kills', 0) - kills_mean) / kills_std_dev if kills_std_dev > 0 else 0

    return z_score, kills_z_score


class LowQuantityRedeploys(MetricReply):
    """Detects players with significantly low redeploys (died a lot)."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        sorted_players = calculate(report)
        if not sorted_players:
            return MetricResult(score=0, message=None)
            
        worst = sorted_players[0]
        z_score, kills_z_score = calculate_outlier(report, worst)

        if not worst or z_score <= 1.0:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 20))

        if kills_z_score > 0.5:
            return MetricResult(score=0, message=None)

        message = random.choice(LOW_REDEPLOYS_MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
