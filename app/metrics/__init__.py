from typing import Optional, List

from app.metrics.metric_reply import MetricReply, MetricResult
from app.metrics.low_kills import LowQtdKills
from app.metrics.waste_bullet import WasteBullet
from app.metrics.high_redeploys import HighQuantityRedeploys
from app.metrics.soft_puncher import SoftPuncher
from app.metrics.kill_stealer import KillStealer

ALL_METRICS = [
    LowQtdKills(),
    WasteBullet(),
    HighQuantityRedeploys(),
    SoftPuncher(),
    KillStealer(),
]


def evaluate_best_metric(player_stats: List[dict]) -> Optional[MetricResult]:
    """
    Evaluate all metrics against the match data and return the most relevant one.

    Args:
        player_stats: List of dicts with keys: player_name, kills, damage, redeploys

    Returns:
        The MetricResult with the highest score, or None if no metric matched.
    """
    if len(player_stats) < 2:
        return None

    results = [
        metric.evaluate(player_stats)
        for metric in ALL_METRICS
    ]

    valid_results = [r for r in results if r.message is not None]

    if not valid_results:
        return None

    valid_results.sort(key=lambda r: r.score, reverse=True)
    return valid_results[0]
