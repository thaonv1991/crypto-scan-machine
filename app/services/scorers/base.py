"""Base scorer class for all scoring engines."""

from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class BaseScorer(ABC):
    """Abstract base class for scoring engines.

    Each engine produces a score from 0 to 100:
    - 0-20: Very poor / high risk
    - 21-40: Below average
    - 41-60: Average
    - 61-80: Good
    - 81-100: Excellent
    """

    engine_name: str = "base"

    @abstractmethod
    def calculate(self, data: dict) -> dict:
        """Calculate score from input data.

        Args:
            data: Dictionary containing relevant data for scoring.

        Returns:
            Dictionary with:
                - score: float (0-100)
                - breakdown: dict with sub-scores and reasoning
        """

    @staticmethod
    def clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
        return max(min_val, min(max_val, value))

    @staticmethod
    def normalize_log(value: float, baseline: float, max_val: float) -> float:
        """Logarithmic normalization for values with wide ranges (volume, market cap, etc.)."""
        import math

        if value <= 0 or baseline <= 0:
            return 0.0
        ratio = value / baseline
        if ratio <= 0:
            return 0.0
        score = (math.log10(ratio + 1) / math.log10(max_val / baseline + 1)) * 100
        return max(0.0, min(100.0, score))
