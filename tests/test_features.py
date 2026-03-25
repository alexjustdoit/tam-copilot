"""
Tests for feature modules using mocked LLM providers.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generators.customers import generate_customers
from data.generators.tickets import generate_tickets
from data.generators.usage import generate_usage
from data.generators.subscriptions import generate_subscriptions
from eval.metrics import score_triage


def _make_mock_provider(return_value, resp_override=None):
    from llm.providers.base import LLMResponse
    resp = resp_override or LLMResponse(
        content="{}",
        provider="mock",
        model="mock",
        latency_ms=100.0,
        estimated_cost_usd=0.0,
    )
    mock = MagicMock()
    mock.complete_structured.return_value = (return_value, resp)
    mock.complete.return_value = resp
    return mock


def test_triage_result_schema():
    from features.ticket_triage import TicketTriageResult

    result = TicketTriageResult(
        priority_recommendation="P1",
        category="Bug",
        sentiment="angry",
        escalation_risk="critical",
        suggested_response="We are escalating this immediately.",
        reasoning="System is down affecting all users.",
    )
    assert result.priority_recommendation == "P1"
    assert result.sentiment == "angry"


def test_score_triage_exact_match():
    output = {"priority_recommendation": "P1", "sentiment": "angry", "escalation_risk": "critical", "category": "Bug"}
    expected = {"priority_recommendation": "P1", "sentiment": "angry", "escalation_risk": "critical", "category": "Bug"}
    score, fields = score_triage(output, expected)
    assert score == 1.0
    assert all(v == 1.0 for v in fields.values())


def test_score_triage_partial():
    output = {"priority_recommendation": "P2", "sentiment": "frustrated", "escalation_risk": "high", "category": "API"}
    expected = {"priority_recommendation": "P1", "sentiment": "angry", "escalation_risk": "critical", "category": "Bug"}
    score, fields = score_triage(output, expected)
    assert 0.0 < score < 1.0


def test_score_triage_missing_fields():
    score, fields = score_triage({}, {})
    # Should not raise — uses defaults
    assert 0.0 <= score <= 1.0


def test_triage_uses_quality_provider_for_p1():
    """P1 tickets should request quality_required=True from router."""
    from features.ticket_triage import TicketTriageResult

    from data.models import SupportTicket
    from datetime import datetime

    p1_ticket = SupportTicket(
        id="test_p1",
        customer_id="cust_001",
        title="Production down",
        description="All users affected.",
        priority="P1",
        category="Bug",
        status="open",
        created_at=datetime.now(),
    )

    mock_result = TicketTriageResult(
        priority_recommendation="P1",
        category="Bug",
        sentiment="angry",
        escalation_risk="critical",
        suggested_response="Escalating now.",
        reasoning="Production is down.",
    )

    with patch("features.ticket_triage.router") as mock_router:
        mock_provider = _make_mock_provider(mock_result)
        mock_router.get_provider.return_value = mock_provider

        from features.ticket_triage import triage_ticket
        result, resp = triage_ticket(p1_ticket)

        # Check quality_required=True was passed for P1
        mock_router.get_provider.assert_called_once_with(quality_required=True)
        assert result.priority_recommendation == "P1"


def test_health_score_breakdown_schema():
    from features.health_score import HealthScoreBreakdown

    score = HealthScoreBreakdown(
        usage_score=20,
        engagement_score=18,
        support_score=15,
        commercial_score=22,
        total_score=75,
        health_tier="Healthy",
        top_strengths=["Strong DAU growth", "High feature adoption"],
        top_risks=["Renewal in 45 days"],
        narrative="Customer is healthy with strong usage trends.",
        recommended_actions=["Schedule renewal call"],
    )
    assert score.total_score == 75
    assert score.health_tier == "Healthy"


def test_churn_risk_schema():
    from features.churn_risk import ChurnRiskAssessment

    risk = ChurnRiskAssessment(
        risk_tier="High",
        churn_probability_pct=75,
        top_risk_factors=["Renewal in 30 days", "Low seat utilization"],
        positive_signals=["No P1/P2 tickets"],
        recommended_actions=["Schedule exec call", "Offer renewal discount"],
        suggested_outreach_message="Subject: Checking in before renewal\n\nHi [Name], ...",
        reasoning="Low utilization and near-term renewal create high risk.",
    )
    assert risk.risk_tier == "High"
    assert len(risk.top_risk_factors) == 2
