import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import SOFT_PUNCHER_MESSAGES


class SoftPuncher(MetricReply):
    """Detects players with high assists compared to kills (Soca-Fofo)."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        # Filter clan members only who have at least 1 assist
        eligible_players = [
            r for r in report 
            if r.get('is_clan_member', False) and r.get('assists', 0) > 0
        ]

        if not eligible_players:
            return MetricResult(score=0, message=None)

        # Calculate ratio: assists / max(kills, 1)
        for p in eligible_players:
            kills = max(p.get('kills', 0), 1)
            p['soft_ratio'] = p.get('assists', 0) / kills

        # Find the one with the highest ratio
        eligible_players.sort(key=lambda x: x['soft_ratio'], reverse=True)
        worst = eligible_players[0]

        # Calculate z-score
        # Calculate mean and std dev of soft_ratio among all players in match
        all_ratios = [p.get('assists', 0) / max(p.get('kills', 0), 1) for p in report]
        eff_mean = sum(all_ratios) / len(all_ratios)
        eff_variance = sum((r - eff_mean) ** 2 for r in all_ratios) / len(all_ratios)
        eff_std_dev = math.sqrt(eff_variance)

        if eff_std_dev == 0 or (worst['soft_ratio'] - eff_mean) <= 0:
            return MetricResult(score=0, message=None)

        z_score = (worst['soft_ratio'] - eff_mean) / eff_std_dev
        
        # Require them to be somewhat of an outlier
        if z_score < 0.8:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 25))
        message = random.choice(SOFT_PUNCHER_MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
