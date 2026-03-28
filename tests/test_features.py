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
        suggested_tags=["Escalation Risk"],
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
        suggested_tags=["Escalation Risk"],
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


# ── Expansion Intelligence ─────────────────────────────────────────────────────

def test_expansion_opportunity_schema():
    from features.expansion import ExpansionOpportunity

    opp = ExpansionOpportunity(
        opportunity_type="Seat Expansion",
        feature_or_product="Advanced Analytics",
        confidence="High",
        estimated_arr_uplift="$20,000–$30,000",
        rationale="Seat utilization is at 95% and DAU/MAU ratio is 0.45.",
        suggested_pitch="Your team is at capacity — adding seats now prevents disruption.",
    )
    assert opp.opportunity_type == "Seat Expansion"
    assert opp.confidence == "High"


def test_expansion_finder_result_schema():
    from features.expansion import ExpansionFinderResult, ExpansionOpportunity

    result = ExpansionFinderResult(
        opportunities=[
            ExpansionOpportunity(
                opportunity_type="Add-on",
                feature_or_product="SSO",
                confidence="Medium",
                estimated_arr_uplift="$5,000–$10,000",
                rationale="Industry peers in FinTech universally use SSO.",
                suggested_pitch="SSO would reduce IT overhead and improve security posture.",
            )
        ],
        total_expansion_potential="$5,000–$10,000",
        best_opportunity_summary="SSO add-on is the clearest win given the industry benchmark gap.",
        recommended_next_step="Demo the SSO feature in the next QBR.",
    )
    assert len(result.opportunities) == 1
    assert result.opportunities[0].feature_or_product == "SSO"


def test_find_expansion_opportunities_calls_provider():
    from datetime import date
    from features.expansion import ExpansionFinderResult, ExpansionOpportunity, find_expansion_opportunities
    from data.models import Customer, Subscription, UsageMetrics

    customer = Customer(
        id="cust_test",
        company_name="Acme Corp",
        industry="SaaS",
        tier="Mid-Market",
        arr=120000.0,
        employees=200,
        tam_owner="Alex",
        contract_start=date(2025, 1, 1),
        renewal_date=date(2026, 12, 31),
    )
    subscription = Subscription(
        customer_id="cust_test",
        plan="Professional",
        seats_purchased=100,
        seats_used=92,
        mrr=10000.0,
        renewal_date=date(2026, 12, 31),
        auto_renew=True,
    )
    usage = [
        UsageMetrics(
            customer_id="cust_test",
            month=date(2026, 2, 1),
            dau=450,
            mau=900,
            api_calls=12000,
            features_adopted=["dashboard", "reports", "api_access"],
            login_frequency=4.5,
        )
    ]
    mock_result = ExpansionFinderResult(
        opportunities=[],
        total_expansion_potential="$15,000–$25,000",
        best_opportunity_summary="Seat expansion is the top opportunity.",
        recommended_next_step="Reach out to discuss seat needs.",
    )

    with patch("features.expansion.router") as mock_router:
        mock_provider = _make_mock_provider(mock_result)
        mock_router.get_provider.return_value = mock_provider

        result, resp = find_expansion_opportunities(customer, usage, subscription)

        mock_router.get_provider.assert_called_once()
        assert result.total_expansion_potential == "$15,000–$25,000"
        assert resp.provider == "mock"


# ── Tag Insights ───────────────────────────────────────────────────────────────

def test_summarize_tag_trends_calls_quality_provider():
    from features.tag_insights import summarize_tag_trends
    from llm.providers.base import LLMResponse

    narrative = "Escalation Risk and SLA Risk are co-occurring frequently."
    mock_resp = LLMResponse(
        content=narrative,
        provider="mock",
        model="mock",
        latency_ms=120.0,
        estimated_cost_usd=0.001,
    )
    mock_provider = MagicMock()
    mock_provider.complete.return_value = mock_resp

    with patch("features.tag_insights.router") as mock_router:
        mock_router.get_provider.return_value = mock_provider

        result, resp = summarize_tag_trends(
            segment="Enterprise",
            tag_counts={"Escalation Risk": 8, "SLA Risk": 5, "Churn Signal": 3},
            total_tickets=40,
            triaged_tickets=16,
        )

        mock_router.get_provider.assert_called_once_with(quality_required=True)
        assert result == narrative
        assert resp.provider == "mock"


def test_summarize_tag_trends_empty_tags():
    """Empty tag_counts should not raise."""
    from features.tag_insights import summarize_tag_trends
    from llm.providers.base import LLMResponse

    mock_resp = LLMResponse(
        content="No tagged tickets yet.",
        provider="mock",
        model="mock",
        latency_ms=80.0,
        estimated_cost_usd=0.0,
    )
    mock_provider = MagicMock()
    mock_provider.complete.return_value = mock_resp

    with patch("features.tag_insights.router") as mock_router:
        mock_router.get_provider.return_value = mock_provider
        result, resp = summarize_tag_trends(
            segment="SMB",
            tag_counts={},
            total_tickets=10,
            triaged_tickets=0,
        )
        assert isinstance(result, str)


# ── Taxonomy ───────────────────────────────────────────────────────────────────

def test_taxonomy_round_trip(tmp_path):
    import json
    from unittest.mock import patch as _patch
    from data.taxonomy import load_taxonomy, save_taxonomy

    taxonomy_file = tmp_path / "taxonomy.json"
    initial = {"tags": ["Escalation Risk", "SLA Risk"], "categories": ["Bug", "Feature Request"]}
    taxonomy_file.write_text(json.dumps(initial))

    with _patch("data.taxonomy.TAXONOMY_PATH", taxonomy_file):
        save_taxonomy(initial)
        loaded = load_taxonomy()

    assert loaded["tags"] == initial["tags"]
    assert loaded["categories"] == initial["categories"]


def test_taxonomy_save_new_tag(tmp_path):
    import json
    from unittest.mock import patch as _patch
    from data.taxonomy import load_taxonomy, save_taxonomy

    taxonomy_file = tmp_path / "taxonomy.json"
    taxonomy_file.write_text(json.dumps({"tags": ["Escalation Risk"], "categories": ["Bug"]}))

    with _patch("data.taxonomy.TAXONOMY_PATH", taxonomy_file):
        data = load_taxonomy()
        data["tags"].append("QBR Worthy")
        save_taxonomy(data)
        reloaded = load_taxonomy()

    assert "QBR Worthy" in reloaded["tags"]
    assert "Escalation Risk" in reloaded["tags"]  # existing tag preserved
