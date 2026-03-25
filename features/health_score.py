from __future__ import annotations

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel

from data.models import Customer, SupportTicket, Subscription, UsageMetrics
from llm.providers.base import LLMResponse
from llm.router import router

SYSTEM_PROMPT = """You are an expert Technical Account Manager analyzing customer health.
Combine quantitative signals and qualitative context to produce an actionable health assessment.
Be specific about what is driving the score and what actions the TAM should take."""


class HealthScoreBreakdown(BaseModel):
    usage_score: int  # 0-25
    engagement_score: int  # 0-25
    support_score: int  # 0-25
    commercial_score: int  # 0-25
    total_score: int  # 0-100
    health_tier: Literal["Healthy", "Neutral", "At Risk", "Critical"]
    top_strengths: List[str]
    top_risks: List[str]
    narrative: str
    recommended_actions: List[str]


def _compute_usage_signals(usage_records: List[UsageMetrics]) -> dict:
    """Compute usage trend and summary from 12 months of data."""
    if not usage_records:
        return {"trend": "unknown", "avg_dau": 0, "features_count": 0}

    sorted_records = sorted(usage_records, key=lambda r: r.month)
    recent = sorted_records[-3:] if len(sorted_records) >= 3 else sorted_records
    early = sorted_records[:3] if len(sorted_records) >= 3 else sorted_records

    avg_recent_dau = sum(r.dau for r in recent) / len(recent)
    avg_early_dau = sum(r.dau for r in early) / len(early)

    if avg_early_dau > 0:
        growth = (avg_recent_dau - avg_early_dau) / avg_early_dau
    else:
        growth = 0

    if growth > 0.1:
        trend = "growing"
    elif growth < -0.1:
        trend = "declining"
    else:
        trend = "stable"

    all_features = set()
    for r in sorted_records:
        all_features.update(r.features_adopted)

    return {
        "trend": trend,
        "growth_pct": round(growth * 100, 1),
        "avg_dau": round(avg_recent_dau),
        "features_count": len(all_features),
        "avg_login_freq": round(
            sum(r.login_frequency for r in recent) / len(recent), 2
        ),
    }


def compute_health_score(
    customer: Customer,
    usage_records: List[UsageMetrics],
    tickets: List[SupportTicket],
    subscription: Optional[Subscription],
) -> Tuple[HealthScoreBreakdown, LLMResponse]:
    usage_signals = _compute_usage_signals(usage_records)

    open_tickets = [t for t in tickets if t.status in ("open", "in_progress")]
    p1_p2_count = sum(1 for t in open_tickets if t.priority in ("P1", "P2"))
    total_tickets_90d = len(tickets)

    seat_util = 0.0
    if subscription:
        seat_util = (
            subscription.seats_used / subscription.seats_purchased
            if subscription.seats_purchased > 0
            else 0
        )

    from datetime import date
    days_to_renewal = (customer.renewal_date - date.today()).days

    user_prompt = f"""Assess health score for this customer:

**Customer:** {customer.company_name} ({customer.tier}, {customer.industry})
**ARR:** ${customer.arr:,.0f}
**Days to Renewal:** {days_to_renewal}

**Usage (last 12 months):**
- Trend: {usage_signals.get('trend', 'unknown')} ({usage_signals.get('growth_pct', 0):+.1f}% DAU change)
- Avg DAU: {usage_signals.get('avg_dau', 0):,}
- Features Adopted: {usage_signals.get('features_count', 0)}
- Avg Login Frequency: {usage_signals.get('avg_login_freq', 0)} logins/user/week

**Support:**
- Open tickets: {len(open_tickets)} (P1/P2: {p1_p2_count})
- Total tickets last 90 days: {total_tickets_90d}

**Commercial:**
- Seat Utilization: {seat_util:.0%}
- Auto-renew: {subscription.auto_renew if subscription else 'unknown'}
- Plan: {subscription.plan if subscription else 'unknown'}

Provide a health score breakdown. Scores: usage_score (0-25), engagement_score (0-25), support_score (0-25), commercial_score (0-25)."""

    provider = router.get_provider()
    return provider.complete_structured(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        schema=HealthScoreBreakdown,
        temperature=0.1,
    )
