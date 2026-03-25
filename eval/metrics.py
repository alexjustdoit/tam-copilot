from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class EvalResult:
    case_id: str
    provider: str
    model: str
    output: dict
    expected: dict
    accuracy_score: float  # 0.0–1.0
    latency_ms: float
    estimated_cost_usd: float
    field_scores: dict = field(default_factory=dict)  # per-field accuracy


@dataclass
class EvalReport:
    provider: str
    model: str
    results: List[EvalResult]

    @property
    def avg_accuracy(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.accuracy_score for r in self.results) / len(self.results)

    @property
    def avg_latency_ms(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.latency_ms for r in self.results) / len(self.results)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.estimated_cost_usd for r in self.results)

    @property
    def cost_per_case_usd(self) -> float:
        if not self.results:
            return 0.0
        return self.total_cost_usd / len(self.results)

    def summary(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "cases": len(self.results),
            "avg_accuracy": round(self.avg_accuracy, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "cost_per_case_usd": round(self.cost_per_case_usd, 5),
        }


def score_triage(output: dict, expected: dict) -> tuple[float, dict]:
    """Score a ticket triage result against ground truth. Returns (0-1, field_scores)."""
    field_scores = {}
    weights = {
        "priority_recommendation": 0.35,
        "sentiment": 0.25,
        "escalation_risk": 0.25,
        "category": 0.15,
    }

    PRIORITY_DISTANCE = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
    RISK_DISTANCE = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    SENTIMENT_DISTANCE = {"positive": 1, "neutral": 2, "frustrated": 3, "angry": 4}

    def ordinal_score(actual, expected_val, scale):
        a = scale.get(actual, 2)
        e = scale.get(expected_val, 2)
        distance = abs(a - e)
        max_distance = len(scale) - 1
        return 1.0 - (distance / max_distance)

    # Priority
    pred_priority = output.get("priority_recommendation", "P3")
    exp_priority = expected.get("priority_recommendation", "P3")
    field_scores["priority_recommendation"] = ordinal_score(pred_priority, exp_priority, PRIORITY_DISTANCE)

    # Sentiment
    pred_sent = output.get("sentiment", "neutral")
    exp_sent = expected.get("sentiment", "neutral")
    field_scores["sentiment"] = ordinal_score(pred_sent, exp_sent, SENTIMENT_DISTANCE)

    # Escalation risk
    pred_risk = output.get("escalation_risk", "low")
    exp_risk = expected.get("escalation_risk", "low")
    field_scores["escalation_risk"] = ordinal_score(pred_risk, exp_risk, RISK_DISTANCE)

    # Category (exact match)
    field_scores["category"] = 1.0 if output.get("category", "").lower() == expected.get("category", "").lower() else 0.0

    total = sum(weights[f] * field_scores[f] for f in weights)
    return round(total, 3), field_scores
