import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import LOW_KILLS_MESSAGES, ZERO_KILLS_MESSAGES


class LowQtdKills(MetricReply):
    """Detects players with significantly low kills compared to the group average."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        # First, check for absolute zero kills (maximum humiliation)
        zero_killers = [r for r in report if r.get('kills', -1) == 0 and r.get('is_clan_member', False)]
        if zero_killers:
            worst = zero_killers[0]
            message = random.choice(ZERO_KILLS_MESSAGES)(worst['player_name'])
            return MetricResult(score=200.0, message=message)

        kills_list = [r['kills'] for r in report]
        kills_mean = sum(kills_list) / len(kills_list)

        # Standard deviation
        variance = sum((k - kills_mean) ** 2 for k in kills_list) / len(kills_list)
        std_dev = math.sqrt(variance)

        # Sort by kills ascending
        sorted_report = sorted(report, key=lambda r: r['kills'])

        # z-score threshold: considered low if 1 std dev below mean
        z_score_threshold = -1.0

        outliers = [
            r for r in sorted_report
            if std_dev > 0 and (r['kills'] - kills_mean) / std_dev < z_score_threshold
            and r.get('is_clan_member', False)
        ]

        if not outliers:
            return MetricResult(score=0, message=None)

        worst = outliers[0]

        z_score = (worst['kills'] - kills_mean) / std_dev if std_dev > 0 else 0
        normalized_score = min(100, max(0, abs(z_score) * 25))

        # Must have at least 2 kills fewer than the average to avoid marginal cases
        if kills_mean - worst['kills'] < 2:
            return MetricResult(score=0, message=None)

        message = random.choice(LOW_KILLS_MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
