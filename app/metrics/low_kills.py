import math
import random

from app.metrics.metric_reply import MetricReply, MetricResult


class LowQtdKills(MetricReply):
    """Detects players with significantly low kills compared to the group average."""

    MESSAGES = [
        lambda name: f"Ei {name}, tu tá só assistindo a partida é?",
        lambda name: f"Pelo visto o {name} comprou ingresso, não fuzil.",
        lambda name: f"O {name} tá mais parado que cone de trânsito.",
        lambda name: f"Chama o {name} pro jogo, ele esqueceu que não é espectador.",
        lambda name: f"{name}, teu controle tá funcionando ou tá no modo demo?",
        lambda name: f"Se o {name} fosse mais parado virava mobília do mapa.",
        lambda name: f"{name}, tá esperando o jogo acabar pra começar a jogar?",
        lambda name: f"Alguém avisa o {name} que ele não tá vendo uma live.",
    ]

    def evaluate(self, report: list[dict]) -> MetricResult:
        if not report:
            return MetricResult(score=0, message=None)

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
        ]

        if not outliers:
            return MetricResult(score=0, message=None)

        worst = outliers[0]

        z_score = (worst['kills'] - kills_mean) / std_dev if std_dev > 0 else 0
        normalized_score = min(100, max(0, abs(z_score) * 25))

        # Must have at least 2 kills fewer than the average to avoid marginal cases
        if kills_mean - worst['kills'] < 2:
            return MetricResult(score=0, message=None)

        message = random.choice(self.MESSAGES)(worst['player_name'])

        return MetricResult(score=normalized_score, message=message)
