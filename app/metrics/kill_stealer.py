import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import KILL_STEALER_MESSAGES


class KillStealer(MetricReply):
    """Detects players with high kills but very low damage (Rouba Kill)."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        # Filter clan members only who have at least 1 kill
        eligible_players = [
            r for r in report 
            if r.get('is_clan_member', False) and r.get('kills', 0) > 0
        ]

        if not eligible_players:
            return MetricResult(score=0, message=None)

        # Calculate ratio: damage / kills
        for p in eligible_players:
            p['dmg_per_kill'] = p.get('damage', 0) / p.get('kills', 1)

        # Find the one with the lowest ratio
        eligible_players.sort(key=lambda x: x['dmg_per_kill'])
        best_stealer = eligible_players[0]

        # Calculate mean and std dev among all players with kills to see how much of an outlier they are
        all_ratios = [
            p.get('damage', 0) / p.get('kills', 1) 
            for p in report if p.get('kills', 0) > 0
        ]

        if not all_ratios:
            return MetricResult(score=0, message=None)

        eff_mean = sum(all_ratios) / len(all_ratios)
        eff_variance = sum((r - eff_mean) ** 2 for r in all_ratios) / len(all_ratios)
        eff_std_dev = math.sqrt(eff_variance)

        if eff_std_dev == 0 or (eff_mean - best_stealer['dmg_per_kill']) <= 0:
            return MetricResult(score=0, message=None)

        # How many std devs below the mean?
        z_score = (eff_mean - best_stealer['dmg_per_kill']) / eff_std_dev
        
        # Require them to be somewhat of an outlier
        if z_score < 0.8:
            return MetricResult(score=0, message=None)

        normalized_score = min(100, max(0, z_score * 25))
        message = random.choice(KILL_STEALER_MESSAGES)(best_stealer['player_name'])

        return MetricResult(score=normalized_score, message=message)
