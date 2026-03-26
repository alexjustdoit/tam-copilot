from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel

from data.models import SupportTicket
from data.taxonomy import load_taxonomy
from llm.providers.base import LLMResponse
from llm.router import router

SYSTEM_PROMPT_TEMPLATE = """You are an expert Technical Account Manager (TAM) assistant.
Your job is to triage customer support tickets and provide actionable assessments.
Be concise, professional, and prioritize customer impact.

Analyze each ticket for:
- Correct priority (P1=system down/data loss, P2=major impact, P3=partial degradation, P4=general inquiry)
- Sentiment and frustration level
- Escalation risk
- A professional suggested response draft
- The most appropriate category from the existing list
- Relevant tags from the existing list that describe the situational and relationship signals

EXISTING CATEGORIES (choose from these):
{categories}

EXISTING TAGS (choose from these — tags describe the situation and relationship signals, not the technical domain):
{tags}

TAG GUIDANCE:
- Escalation Risk: could escalate if not addressed promptly
- Exec Visibility: customer's executive team is aware or involved
- Recurring Issue: same problem has been reported before
- Workaround Active: customer is working around a product gap
- Blocked: customer cannot complete their work
- Training Gap: root cause is user knowledge, not a product defect
- Product Gap: feature does not exist (not a bug)
- Data Issue: data quality, loss, or integrity concern
- SLA Risk: in danger of breaching a contractual commitment
- Churn Signal: explicit frustration language or renewal threat present
- QBR Worthy: worth surfacing in the next Quarterly Business Review

For suggested_tags: only include tags that clearly apply. It is better to suggest fewer, accurate tags than many uncertain ones.
For category: choose the best fit from the existing list.

ONLY use suggested_new_tag or suggested_new_category if no existing option reasonably fits.
New suggestions should be rare — err strongly toward existing taxonomy to prevent bloat.
If you do suggest something new, keep it concise (1-3 words) and distinct from what already exists.
"""


class TicketTriageResult(BaseModel):
    priority_recommendation: Literal["P1", "P2", "P3", "P4"]
    category: str
    suggested_new_category: Optional[str] = None
    suggested_tags: List[str]
    suggested_new_tag: Optional[str] = None
    sentiment: Literal["positive", "neutral", "frustrated", "angry"]
    escalation_risk: Literal["low", "medium", "high", "critical"]
    suggested_response: str
    reasoning: str


def triage_ticket(ticket: SupportTicket) -> Tuple[TicketTriageResult, LLMResponse]:
    """Triage a single ticket. P1s route to quality provider."""
    quality_required = ticket.priority == "P1"
    provider = router.get_provider(quality_required=quality_required)

    taxonomy = load_taxonomy()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        categories=", ".join(taxonomy["categories"]),
        tags=", ".join(taxonomy["tags"]),
    )

    current_tags = ", ".join(ticket.tags) if ticket.tags else "None"
    user_prompt = f"""Triage this support ticket:

Title: {ticket.title}
Category: {ticket.category}
Current Priority: {ticket.priority}
Current Tags: {current_tags}
Status: {ticket.status}

Description:
{ticket.description}

Provide your structured assessment."""

    return provider.complete_structured(
        system=system_prompt,
        user=user_prompt,
        schema=TicketTriageResult,
        temperature=0.1,
    )


def triage_tickets_batch(
    tickets: List[SupportTicket],
    max_workers: int = 5,
) -> List[Tuple[SupportTicket, TicketTriageResult, LLMResponse]]:
    """Triage multiple tickets concurrently using a thread pool."""
    results = []

    def _triage(ticket):
        result, resp = triage_ticket(ticket)
        return ticket, result, resp

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_triage, t): t for t in tickets}
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                ticket = futures[future]
                print(f"Error triaging {ticket.id}: {e}")

    return results
