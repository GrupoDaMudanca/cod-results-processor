from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class MetricResult:
    """Result of a metric evaluation."""
    score: float                  # Relevance score (0-100), higher = more significant
    message: Optional[str]        # Message to send, or None if metric didn't match


class MetricReply(ABC):
    """Abstract base class for match metric evaluators."""

    @abstractmethod
    def evaluate(self, report: List[dict]) -> MetricResult:
        """
        Evaluate the metric against match results.

        Args:
            report: List of player dicts with keys: player_name, kills, damage, redeploys

        Returns:
            MetricResult with score and message.
        """
        pass
