from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel

from data.models import Customer, SupportTicket, Subscription, UsageMetrics
from llm.providers.base import LLMResponse
from llm.router import router

SYSTEM_PROMPT = """You are an expert Technical Account Manager preparing for a Quarterly Business Review (QBR).

You will produce two distinct outputs:

1. TAM Summary (internal, candid): Concise bullet points for the TAM to quickly get up to speed on the account. Include health signals, key risks, renewal urgency, and relationship context. Be honest — this is for the TAM's eyes only.

2. Executive Summary (customer-facing talking points): Polished points the TAM can adapt when opening the QBR with the customer's executive stakeholders. Lean positive and forward-looking, framing the relationship around value delivered and the path ahead. If there is a significant open issue that the customer is already aware of, it is appropriate to acknowledge it honestly and briefly state how it is being addressed — omitting it would seem disingenuous. Do not raise minor issues unprompted.

For all other sections, use specific data points, be concise, and avoid technical jargon unless essential."""


class QBRPrep(BaseModel):
    tam_summary: List[str]  # 5-8 candid internal bullets: health, risks, renewal urgency, relationship context
    executive_summary: List[str]  # 3-5 polished talking points for the TAM to adapt in the meeting; positive/forward-looking but honest about major issues
    business_wins: List[str]  # 3-5 quantified wins
    usage_highlights: List[str]  # 3 key usage metrics to highlight
    open_risks: List[str]  # 2-4 risks to address honestly
    strategic_asks: List[str]  # 2-3 asks from customer (exec sponsor, expansion, etc.)
    renewal_talking_points: List[str]  # 2-3 points to frame the renewal
    suggested_agenda: List[str]  # 5-7 agenda items with estimated time
    follow_up_actions: List[str]  # 3-5 post-QBR next steps


def generate_qbr(
    customer: Customer,
    usage_records: List[UsageMetrics],
    tickets: List[SupportTicket],
    subscription: Optional[Subscription],
    health_score: Optional[int] = None,
) -> Tuple[QBRPrep, LLMResponse]:
    from datetime import date

    resolved_tickets = [t for t in tickets if t.status in ("resolved", "closed")]
    open_tickets = [t for t in tickets if t.status in ("open", "in_progress")]
    days_to_renewal = (customer.renewal_date - date.today()).days

    # 12-month usage summary
    if usage_records:
        sorted_records = sorted(usage_records, key=lambda r: r.month)
        total_api_calls = sum(r.api_calls for r in sorted_records)
        peak_dau = max(r.dau for r in sorted_records)
        latest = sorted_records[-1]
        all_features = set()
        for r in sorted_records:
            all_features.update(r.features_adopted)
    else:
        total_api_calls = peak_dau = 0
        latest = None
        all_features = set()

    seat_util = 0.0
    if subscription and subscription.seats_purchased > 0:
        seat_util = subscription.seats_used / subscription.seats_purchased

    user_prompt = f"""Prepare a QBR for this customer:

**Customer:** {customer.company_name}
**Industry:** {customer.industry} | **Tier:** {customer.tier}
**ARR:** ${customer.arr:,.0f} | **Employees:** {customer.employees:,}
**Health Score:** {health_score if health_score is not None else 'N/A'}/100
**Days to Renewal:** {days_to_renewal}
**TAM:** {customer.tam_owner}

**12-Month Usage Summary:**
- Peak DAU: {peak_dau:,}
- Current DAU: {latest.dau if latest else 'N/A':,}
- Total API calls: {total_api_calls:,}
- Features adopted: {', '.join(sorted(all_features)) if all_features else 'N/A'}

**Support:**
- Tickets resolved this year: {len(resolved_tickets)}
- Currently open: {len(open_tickets)}
- P1/P2 resolved: {sum(1 for t in resolved_tickets if t.priority in ('P1', 'P2'))}

**Commercial:**
- Plan: {subscription.plan if subscription else 'N/A'}
- Seat Utilization: {seat_util:.0%}
- Auto-renew: {subscription.auto_renew if subscription else 'unknown'}

Generate professional QBR talking points that a TAM can use to run a great executive meeting."""

    provider = router.get_provider(quality_required=True)
    return provider.complete_structured(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        schema=QBRPrep,
        temperature=0.3,
    )
