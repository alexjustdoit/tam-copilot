from __future__ import annotations

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel

from data.models import Customer, Subscription, UsageMetrics
from llm.providers.base import LLMResponse
from llm.router import router

ALL_FEATURES = [
    "dashboard", "reports", "api_access", "webhooks", "sso", "audit_logs",
    "bulk_export", "custom_fields", "automations", "integrations",
    "mobile_app", "advanced_analytics", "data_retention", "rbac",
]

INDUSTRY_FEATURE_BENCHMARKS = {
    "FinTech": ["audit_logs", "rbac", "data_retention", "advanced_analytics"],
    "Healthcare": ["audit_logs", "rbac", "data_retention", "sso"],
    "SaaS": ["api_access", "webhooks", "automations", "advanced_analytics"],
    "Retail": ["advanced_analytics", "mobile_app", "integrations", "custom_fields"],
    "Manufacturing": ["integrations", "automations", "bulk_export", "custom_fields"],
}

SYSTEM_PROMPT = """You are a Technical Account Manager identifying expansion opportunities.
Analyze usage patterns, adopted features, and industry benchmarks to find upsell and cross-sell signals.
Be specific about which products/features to recommend and why. Frame everything as customer value."""


class ExpansionOpportunity(BaseModel):
    opportunity_type: Literal["Seat Expansion", "Tier Upgrade", "Add-on", "Cross-sell"]
    feature_or_product: str
    confidence: Literal["Low", "Medium", "High"]
    estimated_arr_uplift: str  # e.g. "$15,000–$25,000"
    rationale: str
    suggested_pitch: str  # 1-2 sentences the TAM can say


class ExpansionFinderResult(BaseModel):
    opportunities: List[ExpansionOpportunity]
    total_expansion_potential: str
    best_opportunity_summary: str
    recommended_next_step: str


def find_expansion_opportunities(
    customer: Customer,
    usage_records: List[UsageMetrics],
    subscription: Optional[Subscription],
) -> Tuple[ExpansionFinderResult, LLMResponse]:
    if usage_records:
        sorted_records = sorted(usage_records, key=lambda r: r.month)
        latest = sorted_records[-1]
        adopted = set(latest.features_adopted)

        # Check if recent usage is near ceiling (high DAU/MAU ratio)
        dau_mau_ratio = latest.dau / latest.mau if latest.mau > 0 else 0
        avg_dau = sum(r.dau for r in sorted_records[-3:]) / min(3, len(sorted_records))
    else:
        adopted = set()
        dau_mau_ratio = 0
        avg_dau = 0
        latest = None

    unadopted = [f for f in ALL_FEATURES if f not in adopted]

    seat_util = 0.0
    if subscription and subscription.seats_purchased > 0:
        seat_util = subscription.seats_used / subscription.seats_purchased

    peer_features = INDUSTRY_FEATURE_BENCHMARKS.get(customer.industry, [])
    missing_peer_features = [f for f in peer_features if f not in adopted]

    user_prompt = f"""Find expansion opportunities for this customer:

**Customer:** {customer.company_name}
**Industry:** {customer.industry} | **Tier:** {customer.tier}
**ARR:** ${customer.arr:,.0f} | **Employees:** {customer.employees:,}

**Current Plan:** {subscription.plan if subscription else 'unknown'}
**Seat Utilization:** {seat_util:.0%} ({subscription.seats_used if subscription else 0} used / {subscription.seats_purchased if subscription else 0} purchased)

**Features Adopted ({len(adopted)}/{len(ALL_FEATURES)}):**
Adopted: {', '.join(sorted(adopted)) if adopted else 'none'}
Not Adopted: {', '.join(sorted(unadopted)) if unadopted else 'none'}

**Industry Peer Benchmark ({customer.industry}):**
Peers typically use: {', '.join(peer_features) if peer_features else 'N/A'}
Missing vs peers: {', '.join(missing_peer_features) if missing_peer_features else 'none — fully adopted!'}

**Usage Signals:**
- Avg DAU (last 3 months): {avg_dau:.0f}
- DAU/MAU ratio: {dau_mau_ratio:.0%} ({'high engagement' if dau_mau_ratio > 0.3 else 'moderate engagement'})

Identify 3-5 specific expansion opportunities. Focus on opportunities with clear customer value."""

    provider = router.get_provider()
    return provider.complete_structured(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        schema=ExpansionFinderResult,
        temperature=0.2,
    )
