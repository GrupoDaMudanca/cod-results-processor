import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult
from app.messages import WASTE_BULLET_MESSAGES


class WasteBullet(MetricReply):
    """Detects players with high damage but poor kill conversion (wasting bullets)."""

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

        # Average damage and kills
        damage_mean = sum(r['damage'] for r in report) / len(report)
        kills_mean = sum(r['kills'] for r in report) / len(report)

        # Players with above-average damage
        high_damage_players = [r for r in report if r['damage'] > damage_mean]
        if not high_damage_players:
            return MetricResult(score=0, message=None)

        # Calculate damage-per-kill efficiency (higher = worse)
        player_efficiencies = []
        for r in high_damage_players:
            kills = r['kills'] if r['kills'] > 0 else 1
            player_efficiencies.append({
                **r,
                'damage_per_kill': r['damage'] / kills
            })

        # Mean and std dev of efficiency
        eff_mean = sum(p['damage_per_kill'] for p in player_efficiencies) / len(player_efficiencies)
        eff_variance = sum(
            (p['damage_per_kill'] - eff_mean) ** 2 for p in player_efficiencies
        ) / len(player_efficiencies)
        eff_std_dev = math.sqrt(eff_variance)

        # Filter: high damage + below-average kills + significantly worse efficiency
        outliers = [
            p for p in player_efficiencies
            if p['kills'] < kills_mean
            and eff_std_dev > 0
            and (p['damage_per_kill'] - eff_mean) / eff_std_dev > 0.8
            and p.get('is_clan_member', False)
        ]

        if not outliers:
            return MetricResult(score=0, message=None)

        # Worst efficiency
        outliers.sort(key=lambda p: p['damage_per_kill'], reverse=True)
        worst = outliers[0]

        z_score = (worst['damage_per_kill'] - eff_mean) / eff_std_dev if eff_std_dev > 0 else 0
        normalized_score = min(100, max(0, z_score * 25))

        message = random.choice(WASTE_BULLET_MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
