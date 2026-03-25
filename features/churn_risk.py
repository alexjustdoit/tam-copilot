from __future__ import annotations

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel

from data.models import Customer, SupportTicket, Subscription, UsageMetrics
from llm.providers.base import LLMResponse
from llm.router import router

SYSTEM_PROMPT = """You are an expert Technical Account Manager specializing in churn prevention.
Analyze customer signals to identify churn risk and provide actionable recommendations.
Be specific about the top risk factors and what the TAM should do this week."""


class ChurnRiskAssessment(BaseModel):
    risk_tier: Literal["Low", "Medium", "High", "Critical"]
    churn_probability_pct: int  # 0-100
    top_risk_factors: List[str]  # 3 items
    positive_signals: List[str]  # 1-3 items
    recommended_actions: List[str]  # 3-5 prioritized actions
    suggested_outreach_message: str  # Draft email subject + first paragraph
    reasoning: str


def assess_churn_risk(
    customer: Customer,
    usage_records: List[UsageMetrics],
    tickets: List[SupportTicket],
    subscription: Optional[Subscription],
    health_score: Optional[int] = None,
) -> Tuple[ChurnRiskAssessment, LLMResponse]:
    from datetime import date

    days_to_renewal = (customer.renewal_date - date.today()).days
    seat_util = 0.0
    if subscription and subscription.seats_purchased > 0:
        seat_util = subscription.seats_used / subscription.seats_purchased

    # Usage trend
    if usage_records:
        sorted_records = sorted(usage_records, key=lambda r: r.month)
        if len(sorted_records) >= 6:
            recent_avg = sum(r.dau for r in sorted_records[-3:]) / 3
            mid_avg = sum(r.dau for r in sorted_records[-6:-3]) / 3
            usage_trend = "declining" if recent_avg < mid_avg * 0.85 else (
                "growing" if recent_avg > mid_avg * 1.1 else "stable"
            )
        else:
            usage_trend = "insufficient data"
    else:
        usage_trend = "no data"

    open_tickets = [t for t in tickets if t.status in ("open", "in_progress")]
    frustrated_tickets = [
        t for t in tickets
        if any(word in t.description.lower() for word in
               ["unacceptable", "considering alternatives", "losing money", "unresponsive", "escalate"])
    ]

    user_prompt = f"""Assess churn risk for this customer:

**Customer:** {customer.company_name}
**Tier:** {customer.tier} | **ARR:** ${customer.arr:,.0f}
**Days to Renewal:** {days_to_renewal} {'⚠️ URGENT' if days_to_renewal < 90 else ''}

**Health Score:** {health_score if health_score is not None else 'Not calculated'}/100

**Usage:**
- Trend: {usage_trend}
- Seat Utilization: {seat_util:.0%} {'⚠️ LOW' if seat_util < 0.5 else '✓ HEALTHY' if seat_util > 0.7 else ''}

**Support Signals:**
- Open tickets: {len(open_tickets)}
- Frustrated/escalation language detected in {len(frustrated_tickets)} tickets
- P1/P2 open: {sum(1 for t in open_tickets if t.priority in ('P1', 'P2'))}

**Commercial:**
- Auto-renew enabled: {subscription.auto_renew if subscription else 'unknown'}
- Plan: {subscription.plan if subscription else 'unknown'}

Provide a comprehensive churn risk assessment with specific, actionable recommendations."""

    provider = router.get_provider(quality_required=(days_to_renewal < 90))
    return provider.complete_structured(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        schema=ChurnRiskAssessment,
        temperature=0.1,
    )
