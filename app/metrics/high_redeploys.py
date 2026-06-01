import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import HIGH_REDEPLOYS_MESSAGES


class HighQuantityRedeploys(MetricReply):
    """Detects players with significantly high redeploys compared to the group."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        redeploys_list = [r['redeploys'] for r in report]
        redeploys_mean = sum(redeploys_list) / len(redeploys_list)

        # Standard deviation
        variance = sum((rd - redeploys_mean) ** 2 for rd in redeploys_list) / len(redeploys_list)
        std_dev = math.sqrt(variance)

        # Sort by redeploys descending
        sorted_report = sorted(report, key=lambda r: r['redeploys'], reverse=True)

        min_redeploys = 3
        z_score_threshold = 1.2

        outliers = [
            r for r in sorted_report
            if r['redeploys'] >= min_redeploys
            and std_dev > 0
            and (r['redeploys'] - redeploys_mean) / std_dev > z_score_threshold
            and r.get('is_clan_member', False)
        ]

        if not outliers:
            return MetricResult(score=0, message=None)

        worst = outliers[0]

        z_score = (worst['redeploys'] - redeploys_mean) / std_dev if std_dev > 0 else 0
        normalized_score = min(100, max(0, z_score * 20))

        # If the player has above-average kills, redeploys are less problematic
        kills_list = [r['kills'] for r in report]
        kills_mean = sum(kills_list) / len(kills_list)
        kills_variance = sum((k - kills_mean) ** 2 for k in kills_list) / len(kills_list)
        kills_std_dev = math.sqrt(kills_variance)

        kills_z_score = (worst['kills'] - kills_mean) / kills_std_dev if kills_std_dev > 0 else 0

        if kills_z_score > 0.5:
            return MetricResult(score=0, message=None)

        message = random.choice(HIGH_REDEPLOYS_MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
